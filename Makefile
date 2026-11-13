# pdc: the Extended Publet Decimal Classification.

# The suite runs against bin/pdc, with nothing installed; coverage is anchored to the checkout.
FUNCTIONAL_ENV = PDC_BIN_DIR=$(CURDIR)/bin COVERAGE_ROOT=$(CURDIR)
EDITABLE =
include pubkit-python.mk

import: ## Regenerate data/pdc/ from the UDC Summary that data/udc-summary/source.json pins
	bin/pdc import

import-check: ## Fail if data/pdc/ differs from what the pinned UDC Summary gives
	bin/pdc import --check

check: sync-check import-check functional ## Everything CI runs
