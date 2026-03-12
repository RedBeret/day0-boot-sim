.PHONY: install test up down demo

VENV=.venv
PYTHON=$(VENV)/bin/python
PIP=$(VENV)/bin/pip

install:
	python3.12 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"

test:
	PYTHONPATH=src pytest -q

up:
	docker compose up -d --build

down:
	docker compose down --remove-orphans

demo:
	docker compose up -d --build
