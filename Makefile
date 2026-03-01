UV ?= uv
APP ?= app.py
BACKEND ?= backend.py

.PHONY: setup ui backend dev

setup:
	$(UV) venv .venv
	$(UV) pip install -r requirements.txt

ui:
	$(UV) run streamlit run $(APP)

backend:
	$(UV) run python $(BACKEND)

dev: ui
