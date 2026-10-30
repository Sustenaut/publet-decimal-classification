# Changelog

## Unreleased

### Added
- The UDC Summary (2,452 classes; Finto's SKOS, retrieved 2026-10-14, pinned by sha256) imported as 2,430 subject concepts at their UDC notations, each placed under its broader classes; the 22 classes with no label are left out and listed in data/pdc/REPORT.md.
- PDC codes: a UDC notation, `~`, and a decimal PDC number; `pdc code` checks them and names the broader class.
- tools/publish.py signs the import into a publet workspace with the `pub` on PATH, with a stated --created and a given key. It no longer takes the binary to run as `--pub`, which SonarCloud flagged as command injection (pythonsecurity:S8701).
- The import signed by the PDC steward key (pub:sha2-256:ue7bjgletvpfendw4dptudm64oaaqaoia3pu7vnao6xq6fq5o6jq): 2,430 concepts, 2,428 placements and their signatures in corpus/objects/, with each code's CID in data/pdc/cids.json.
- `pip install` installs the PDC as the package `publet-decimal-classification`: the `pdc` command, and `pdc.classes()` and `pdc.cids()` reading the generated data it carries as `pdc.data`.
- The signed objects are the members of the PDC's corpus, in corpus/objects/, so its releases are signed by the PDC steward key as well.
