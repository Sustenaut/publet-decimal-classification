# pdc: the Extended Publet Decimal Classification.
.PHONY: help venv functional import import-check lock sync-check check

help: ## Available targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sed 's/:.*## /\t/'

venv: ## Create .venv from the hash-locked requirements (rdflib, and the test suite's)
	python3 -m venv .venv
	.venv/bin/pip install --quiet --require-hashes -r tests/requirements.lock

functional: ## The Gherkin suite against bin/pdc, with its coverage in coverage/coverage.xml
	rm -rf coverage && mkdir coverage
	cd tests && PDC_BIN_DIR=$(CURDIR)/bin COVERAGE_RCFILE=$(CURDIR)/pyproject.toml COVERAGE_FILE=$(CURDIR)/coverage/.coverage \
	  ../.venv/bin/coverage run -m pytest -q $(PYTEST_ARGS)
	COVERAGE_FILE=coverage/.coverage .venv/bin/coverage combine -q
	COVERAGE_FILE=coverage/.coverage .venv/bin/coverage xml -q

import: ## Regenerate data/pdc/ from the UDC Summary that data/udc-summary/source.json pins
	bin/pdc import

import-check: ## Fail if data/pdc/ differs from what the pinned UDC Summary gives
	bin/pdc import --check

lock: ## Pin tests/requirements.txt with hashes
	.venv/bin/pubkit lock

sync-check: ## Fail if pubkit's managed files drifted
	.venv/bin/pubkit sync --check

check: sync-check import-check functional ## Everything CI runs
