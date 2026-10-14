# Changelog

## Unreleased

### Added
- The UDC Summary (2,452 classes; Finto's SKOS, retrieved 2026-10-14, pinned by sha256) imported as 2,430 subject concepts at their UDC notations, each placed under its broader classes; the 22 classes with no label are left out and listed in data/pdc/REPORT.md.
- PDC codes: a UDC notation, `~`, and a decimal PDC number; `pdc code` checks them and names the broader class.
- tools/publish.py signs the import into a publet workspace with `pub`.
