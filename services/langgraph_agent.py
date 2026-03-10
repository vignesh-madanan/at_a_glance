"""
LangGraph-based NYC Transit Navigation Agent.

A conversational agent that answers questions about NYC subway, bus, and ferry
using real-time MTA data tools.
"""

import os
import json
import requests
from typing import Annotated, Sequence
from datetime import datetime, timezone
import pytz

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing_extensions import TypedDict

# ---------------------------------------------------------------------------
# Tools – real MTA data
# ---------------------------------------------------------------------------

NYC_TZ = pytz.timezone("America/New_York")

MTA_FEEDS = {
    "1234567GS": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs",
    "ACE":       "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace",
    "BDFM":      "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm",
    "NQRW":      "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw",
    "JZ":        "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-jz",
    "L":         "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-l",
    "SIR":       "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-si",
}

ALERTS_URL = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/camsys%2Fall-alerts"

BUSTIME_BASE = "https://bustime.mta.info/api/siri/stop-monitoring.json"
BUSTIME_KEY = os.getenv("MTA_BUSTIME_API_KEY", "")

FERRY_GTFS_URL = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/camsys%2Fnyc-ferry-gtfs"


def _now_nyc() -> datetime:
    return datetime.now(NYC_TZ)


@tool
def get_subway_arrivals(station_name: str, line: str) -> str:
    """
    Get upcoming subway arrival times for a given station and line.
    station_name: the station name (e.g. 'Union Square - 14th St')
    line: subway line letter/number (e.g. '4', 'N', 'L')
    """
    try:
        from services.train import SubwayService
        svc = SubwayService()
        arrivals = svc.get_arrivals(station_name, line, "")
        if not arrivals:
            return f"No upcoming {line} trains found at {station_name}."
        lines_out = []
        for a in arrivals[:5]:
            mins = a.get("minutes", "?")
            direction = a.get("direction", "")
            lines_out.append(f"  • {mins} min ({direction})")
        return f"Upcoming {line} trains at {station_name}:\n" + "\n".join(lines_out)
    except Exception as e:
        return f"Could not fetch subway arrivals: {e}"


@tool
def get_bus_arrivals(bus_route: str, stop_name: str) -> str:
    """
    Get upcoming bus arrival times for a given bus route and stop.
    bus_route: the bus route (e.g. 'M14A', 'B63')
    stop_name: a description of the stop location (e.g. '14th St & Union Sq E')
    """
    try:
        from services.bus import BusService
        svc = BusService()
        arrivals = svc.get_arrivals(bus_route, stop_name, "Eastbound")
        if not arrivals:
            return f"No upcoming {bus_route} buses found near {stop_name}."
        lines_out = []
        for a in arrivals[:5]:
            mins = a.get("minutes", "?")
            lines_out.append(f"  • {mins} min")
        return f"Upcoming {bus_route} buses at {stop_name}:\n" + "\n".join(lines_out)
    except Exception as e:
        return f"Could not fetch bus arrivals: {e}"


@tool
def get_ferry_schedule(terminal: str) -> str:
    """
    Get upcoming NYC Ferry departure times from a terminal.
    terminal: terminal name (e.g. 'Wall St/Pier 11', 'East 34th Street', 'Rockaway')
    """
    try:
        from services.ferry import FerryService
        svc = FerryService()
        departures = svc.get_departures(terminal)
        if not departures:
            return f"No upcoming ferry departures found at {terminal}."
        lines_out = []
        for d in departures[:5]:
            t = d.get("time", "?")
            route = d.get("route", "")
            lines_out.append(f"  • {t} → {route}")
        return f"Upcoming ferries at {terminal}:\n" + "\n".join(lines_out)
    except Exception as e:
        return f"Could not fetch ferry schedule: {e}"


@tool
def get_service_alerts(line: str = "") -> str:
    """
    Get current MTA service alerts.
    line: optional subway line/bus route to filter by (leave empty for all alerts)
    """
    try:
        from services.alerts import AlertsService
        svc = AlertsService()
        alerts = svc.get_alerts()
        if not alerts:
            return "No active service alerts at this time."
        if line:
            alerts = [a for a in alerts if line.upper() in a.get("affected_routes", [])]
        if not alerts:
            return f"No active service alerts for {line}."
        parts = []
        for a in alerts[:5]:
            header = a.get("header", "")
            description = a.get("description", "")
            parts.append(f"• {header}: {description[:120]}")
        return "Current service alerts:\n" + "\n".join(parts)
    except Exception as e:
        return f"Could not fetch alerts: {e}"


@tool
def get_transit_info(query: str) -> str:
    """
    Answer general NYC transit questions: how to get between places,
    transfer info, accessibility, fares, MetroCard, OMNY, etc.
    query: a natural language transit question
    """
    # This tool provides static knowledge the LLM can use as a lookup hook.
    # The LLM itself will answer these from its training knowledge, but having
    # it as a tool keeps the agent structured.
    info = {
        "fare": "NYC subway/bus base fare is $2.90 (2024). Ferry is $4.00.",
        "omny": "OMNY contactless tap-to-pay accepted on all subway/bus. Daily cap $13.05, weekly cap $34.",
        "metrocard": "MetroCard works on all subways and buses. 30-day unlimited: $132.",
        "transfers": "Free transfer between subway and bus (or bus to bus) within 2 hours with OMNY or unlimited MetroCard.",
        "accessibility": "Many stations have elevators. Check mta.info/accessibility for ADA-compliant station list.",
        "express": "Express trains (2,3,4,5,A,D,E,F,J,Z,N,Q) skip local stops and are faster for long distances.",
    }
    q = query.lower()
    for k, v in info.items():
        if k in q:
            return v
    return f"General NYC transit info for: {query}"


TOOLS = [
    get_subway_arrivals,
    get_bus_arrivals,
    get_ferry_schedule,
    get_service_alerts,
    get_transit_info,
]

# ---------------------------------------------------------------------------
# LangGraph Agent
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an expert NYC transit navigation assistant with real-time access \
to MTA subway, bus, and NYC Ferry data.

You help users:
- Find the best route between two locations in NYC
- Check real-time subway, bus, and ferry arrivals
- Look up service alerts and delays
- Answer questions about fares, MetroCard, OMNY, transfers, and accessibility
- Recommend the fastest or most convenient transit option

Always be concise and practical. When fetching real-time data, use the available tools. \
If you don't have a specific stop ID, try with the stop name or explain what info you need. \
Use NYC transit terminology (e.g. "uptown", "downtown", "local", "express").
"""


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


def _build_graph() -> StateGraph:
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    llm = ChatAnthropic(
        model="claude-sonnet-4-6",
        api_key=api_key or None,
        temperature=0,
    ).bind_tools(TOOLS)

    tool_node = ToolNode(TOOLS)

    def agent_node(state: AgentState):
        messages = list(state["messages"])
        # Prepend system prompt if not already present
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
        response = llm.invoke(messages)
        return {"messages": [response]}

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")

    return graph.compile()


# Singleton compiled graph (rebuilt lazily)
_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = _build_graph()
    return _graph


def chat(history: list[dict], user_message: str) -> str:
    """
    Run one turn of the agent.

    history: list of {"role": "user"|"assistant", "content": str}
    user_message: the new user message
    Returns: assistant reply string
    """
    messages: list[BaseMessage] = []
    for m in history:
        if m["role"] == "user":
            messages.append(HumanMessage(content=m["content"]))
        else:
            messages.append(AIMessage(content=m["content"]))
    messages.append(HumanMessage(content=user_message))

    graph = get_graph()
    result = graph.invoke({"messages": messages})
    last = result["messages"][-1]
    return last.content if hasattr(last, "content") else str(last)
