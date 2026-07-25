.PHONY: help create-venv install install-dev format check type spell test ci clean

PYCMD ?= python
VENV ?= .venv

ifeq ($(OS),Windows_NT)
    VENV_PY := $(VENV)\Scripts\python.exe
	RM = del /Q
	RMD = rmdir /S /Q
else
    VENV_PY := $(VENV)/bin/python
	RM = rm -r
	RMD = rm -rf
endif

ifeq ($(wildcard $(VENV_PY)),)
    PYTHON := $(PYCMD)
else
    PYTHON := $(VENV_PY)
endif

PIP = $(PYTHON) -m pip

.DEFAULT_GOAL := help

help:
	@echo Available targets:
	@echo   create-venv   Create a Python virtual environment and upgrade pip
	@echo   install       Install runtime dependencies, will use venv if it exists
	@echo   install-dev   Install development dependencies including lint/test tools
	@echo   format        Automatically fix linting and formatting issues in source code
	@echo   check         Check linting and formatting without modifying files
	@echo   type          Run mypy type checks
	@echo   spell         Check for common spelling mistakes in source and docs
	@echo   test          Run pytest with coverage reports
	@echo   ci            Run full CI checks: check + type + test
	@echo   clean         Remove virtual environment and temporary caches

create-venv:
	$(PYCMD) -m venv $(VENV)
	$(PIP) install --upgrade pip

install:
	$(PIP) install --upgrade -r requirements.txt

install-dev: install
	$(PIP) install --upgrade -r requirements-dev.txt

format:
	$(PYTHON) -m ruff format src tests
	$(PYTHON) -m ruff check --fix src tests

check:
	$(PYTHON) -m ruff format --check src tests
	$(PYTHON) -m ruff check src tests

type:
	$(PYTHON) -m mypy src

spell:
	codespell

test:
	$(PYTHON) -m pytest --cov=immich2gpx --cov-report=term-missing --cov-report=html

ci: check type spell test

clean:
	-$(RM) .coverage coverage.xml
	-$(RMD) .mypy_cache .pytest_cache .ruff_cache htmlcov
