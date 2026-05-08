.PHONY: help install format lint validate check clean

VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
YAMLFIX := $(VENV)/bin/yamlfix
YAMLLINT := $(VENV)/bin/yamllint
CATALOG := oauth-sdk-conformance-catalog.yaml

help:
	@echo "Targets:"
	@echo "  install   Create .venv and install dev dependencies"
	@echo "  format    Apply yamlfix formatting to the catalog"
	@echo "  lint      Run yamllint (read-only)"
	@echo "  validate  Run schema + duplicate-id checks against the catalog"
	@echo "  check     Run lint + validate (no writes)"
	@echo "  clean     Remove .venv"

$(VENV)/bin/activate: requirements-dev.txt
	python3 -m venv $(VENV)
	$(PIP) install --quiet --upgrade pip
	$(PIP) install --quiet -r requirements-dev.txt
	@touch $(VENV)/bin/activate

install: $(VENV)/bin/activate

format: install
	YAMLFIX_CONFIG_PATH=.yamlfix.toml $(YAMLFIX) $(CATALOG)

lint: install
	$(YAMLLINT) .

validate: install
	$(PY) scripts/validate_catalog.py

check: lint validate

clean:
	rm -rf $(VENV)
