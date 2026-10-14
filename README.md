# PDC: the Extended Publet Decimal Classification

The PDC is a public subject classification for publets. It is the
[UDC Summary](https://www.udcsummary.info) (about 2,400 classes of the
Universal Decimal Classification), with each class imported as a concept
publet under its UDC code. Narrower PDC classes extend it where UDC is too
coarse. Each concept is a `definitional` claim with `defines.sort:
"concept"` (publet spec Section 5.9.1), so it can be reviewed, disputed and
revised like any other publet.

## What is here

| Path | What it is |
|---|---|
| `data/udc-summary/udcs.ttl` | The UDC Summary's SKOS data, as downloaded. |
| `data/udc-summary/source.json` | Where and when it was downloaded, and its sha256. |
| `data/pdc/udc-summary.json` | One concept claim body per labelled UDC class, with its broader classes. Generated. |
| `data/pdc/REPORT.md` | What was imported, what was left out and why. Generated. |
| `bin/pdc` | `pdc import [--check]` regenerates `data/pdc/`, and `pdc code CODE...` checks PDC codes. |
| `tools/publish.py` | Signs the claims into a publet workspace with `pub`, then files the `classifies` annotations that place each class under its broader ones. |

```sh
make venv            # .venv from the hash-locked requirements
make import          # regenerate data/pdc/ from the pinned source
make check           # sync-check, import-check, and the Gherkin suite
bin/pdc code 631.5~12
tools/publish.py --pub=PATH/TO/pub --workspace=DIR
```

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

## The concept claims

Each labelled class becomes a subject concept: a concept with neither a
`kind` nor a `relation` (spec Section 5.9.1, schryer/publet#49).

- `pdc` is the notation.
- `name` is the English preferred label.
- `boundary.includes` holds the English scope notes, where a class has
  any.
- `matches` names its `http://udcdata.info/` URI.
- The claim cites that URI, with the attribution as the citation's note.

A PDC edition, a document listing one concept lineage per code, comes
later. So do the PDC's own classes.

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
