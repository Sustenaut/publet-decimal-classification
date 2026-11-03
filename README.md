# PDC: the Extended Publet Decimal Classification

The PDC is a public subject classification for publets. It is the
[UDC Summary](https://www.udcsummary.info) (about 2,400 classes of the
Universal Decimal Classification), with each class imported as a subject
concept under its UDC code. Narrower PDC classes extend it where UDC is too
coarse. The classes directly under one class are defined together in one
family, a `definitional` claim with `defines.sort: "family"` (publet spec
Section 5.9.1). A definition is changed by a new version and is not debated.
Anyone may propose a change, as that section describes.

## What is here

| Path | What it is |
|---|---|
| `data/udc-summary/udcs.ttl` | The UDC Summary's SKOS data, as downloaded. |
| `data/udc-summary/source.json` | Where and when it was downloaded, and its sha256. |
| `data/pdc/udc-summary.json` | Each labelled UDC class: its code, URI, name, boundary and broader class. Generated. |
| `data/pdc/families.json` | The families, with their auxiliary groups, groupings and counts. Generated. |
| `data/pdc/REPORT.md` | What was imported, what was left out and why. Generated. |
| `bin/pdc` | `pdc import [--check]` regenerates `data/pdc/`, and `pdc code CODE...` checks PDC codes. |
| `corpus/objects/` | The import as signed publets, one file per object, named by CID: the members of the PDC's corpus. |
| `pyproject.toml` | The `publet-decimal-classification` Python package: `pdc` and its data. |
| `data/pdc/cids.json` | The edition's CID, and each code's family, by CID. |
| `tools/publish.py` | Composes the families and the edition into a new corpus with the `pub` on PATH, and signs them with the key in `--key` (a `.publet` directory). |

```sh
make venv            # .venv from the hash-locked requirements
make import          # regenerate data/pdc/ from the pinned source
make check           # sync-check, import-check, and the Gherkin suite
bin/pdc code 631.5~12
tools/publish.py --key=DIR/.publet --corpus=NEW --release=X.Y.Z --created=2026-10-15T09:00:00Z
```

## Which publet

`pub-version.txt` names the releases of publet's `pub` this repository is built
with, `^0.3`: the first with families and the 1 MiB object limit. `pub` refuses to
run here otherwise, and `tools/publish.py` checks it first. Install it with

```sh
cargo install --locked --git https://github.com/Sustenaut/publet --tag v0.3.0 publet-cli pub-ls pub-cat pub-store
```

## Installing

```sh
pip install "git+https://github.com/Sustenaut/publet-decimal-classification"
pdc code 631.5~12
```

The package carries the generated data as `pdc.data`, so it can be used
from Python without a checkout:

```python
import pdc
from pdc import code

pdc.classes()       # every imported class: code, UDC URI, broader class, name, boundary
pdc.family_data()   # the families, with their auxiliary groups, groupings and counts
pdc.cids()          # each code's signed family, by CID
pdc.edition()       # the signed edition this data is, by CID
code.broader("631.5~12")       # "631.5~1"
```

## Releases

The PDC is released with [pubrel](https://github.com/Sustenaut/pubrel),
as the other pub* packages are, from the corpus in `corpus/`, and signed by
the PDC steward key (`release.json`). Each release is tagged, and installs
with `pip install "git+https://github.com/Sustenaut/publet-decimal-classification@TAG"`.
A pull request that changes `pdc/`, `data/pdc/` or `pyproject.toml`
records its change with `pubrel add`. A data change is a patch release
(`added` or `fixed`); a change to the structure of the data (the files'
shapes, or the claims') is recorded as `changed`, the breaking part of the
version. `CHANGELOG.md` is generated from the releases.

## The signed families

`corpus/objects/` holds the import as signed publets: 573 families defining the
2,430 classes, the edition listing every family by its CID, one `sig` for each
of those (purpose `authored`), the package publet, the key object, and the
domain with its two signed generation records. `data/pdc/cids.json` gives the
edition's CID and each code's family. The concept claims and `classifies`
annotations of release 0.1.0 are in git history and its tag, `v0.1.0`; the
families start a new domain, because a generation may not lose members.

They are signed by the **PDC steward key**,
`pub:sha2-256:ue7bjgletvpfendw4dptudm64oaaqaoia3pu7vnao6xq6fq5o6jq`
(principal `human`, label "PDC steward key"). It signs the UDC Summary
import, and it is the corpus's key, so it signs the PDC's releases too.
Its secret is kept the way the pub* release keys are: in the
gitignored `corpus/.publet/` of the checkout that signs, never committed.
The run was

    tools/publish.py --key=corpus/.publet --corpus=NEW --release=0.2.0 --created=CREATED

with `pub` v0.3.0, after which `NEW`'s objects, lock, corpus file and store
replaced the corpus here. Release 0.1.0's store is kept beside the new one as
`corpus/.publet/objects-v0.1.0.redb`.

## Codes

A UDC Summary class keeps its UDC notation as its PDC code: `631` is
"Agriculture in general". A PDC class narrower than a UDC class is written
as the UDC notation, `~`, and a PDC number:

    631.5~1     narrower than the UDC class 631.5
    631.5~12    narrower than 631.5~1

- **The separator is `~`.** UDC notation never uses it. No notation in
  the UDC Summary does (`pdc import` refuses a source where one does), and
  `~` is not among the signs of UDC syntax. So a PDC code can never collide
  with a present or future UDC code. `~` is also an unreserved character
  in URLs and is valid in file names.
- **PDC numbers are decimal, one digit per level**, as UDC's are. The
  broader class is read from the code: drop the last digit, and drop the
  `~` too once no digits remain. Each level holds ten classes, `0` to `9`.
- **UDC classes are placed by UDC's own hierarchy**, `skos:broader`, not
  by their notation. In the UDC Summary, 867 broader links are not
  notation prefixes: for example, `631`'s broader class is `631/635`.

## The families

Each labelled class is a subject concept (spec Section 5.9.1), defined in the
family under its broader class. The top family holds the two UDC roots, `-` and
`----`. `data/pdc/REPORT.md` gives the numbers.

- `pdc` is the notation, `name` the English preferred label, and
  `boundary.includes` the English scope notes, where a class has any.
- `matches` names its `http://udcdata.info/` URI.
- `children: true` marks a class that heads a family of its own.
- `auxiliaries` holds the special auxiliaries that start in the family. One is
  told by its notation, as UDC writes it: `62-1`, `` 81`1 ``, `7.01`.
- `grouping` names the auxiliary grouping the family's classes may use: the
  common tables, plus the special auxiliaries of its parent and every class
  above it. Group and grouping numbers never change meaning, so each import
  keeps the numbers already in `data/pdc/families.json`.

A family cites the UDC Summary, with the attribution as the citation's note. An
edition lists every family by its exact CID, and is what a reader pins.

## Licence and attribution

The data is derived from the **UDC Summary**, © UDC Consortium. It is
released under
[Creative Commons Attribution-ShareAlike 3.0](http://creativecommons.org/licenses/by-sa/3.0/)
and served as SKOS by [Finto](https://finto.fi/udcs/en/) (National Library
of Finland). The original file is kept unchanged in `data/udc-summary/`
under its own licence.

The PDC adapts it. The PDC's data (`data/pdc/`, and any concept publets
made from it) is published under
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) (see
`data/LICENSE`), which CC BY-SA 3.0 allows for an adaptation. It is
attributed to the UDC Consortium as the source of the UDC Summary. The
UDC Consortium does not endorse the PDC.

The code (`pdc/`, `bin/`, `tools/`, `tests/`) is under the Apache License
2.0 (see `LICENSE`).
