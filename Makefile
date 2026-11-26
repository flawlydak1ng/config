PYTHON ?= python3
VENV ?= .venv
BIN = $(VENV)/bin/python
export PYTHONPATH := src

.PHONY: setup test run
setup:
	$(PYTHON) -m venv $(VENV)
	$(BIN) -m pip install -r requirements.txt

test:
	$(BIN) -m unittest discover -s tests -v

run:
	$(BIN) -m configxml --input "$(INPUT)" --output "$(OUTPUT)"
