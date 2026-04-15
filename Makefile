.PHONY: install run draft load-data dev clean setup

PYTHON = .venv/bin/python
PIP = .venv/bin/pip

setup:
	python3 -m venv .venv
	$(PIP) install -r requirements.txt

install:
	$(PIP) install -r requirements.txt

run:
	.venv/bin/uvicorn src.app:app --host 0.0.0.0 --port 8000

dev:
	.venv/bin/uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload

load-data:
	$(PYTHON) scripts/load_players.py

load-csv:
	$(PYTHON) scripts/load_players.py --csv $(CSV)

draft:
	$(PYTHON) scripts/run_draft.py

clean:
	rm -rf tournament_data/*.json
	@echo "Tournament data cleaned."

reset: clean load-data draft
	@echo "Tournament reset complete."
