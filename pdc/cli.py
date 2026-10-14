"""pdc: import the UDC Summary, and check PDC codes.

    pdc import [--check] [--data=DIR] [--out=DIR]
    pdc code CODE...
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pdc import code, importer

ROOT = Path(__file__).resolve().parent.parent


def _udc_notations(out: Path) -> set[str]:
    data = json.loads((out / "udc-summary.json").read_text())
    return {c["pdc"] for c in data["classes"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pdc", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    imp = sub.add_parser("import", help="write data/pdc/ from the pinned UDC Summary")
    imp.add_argument("--check", action="store_true", help="fail if data/pdc/ is stale")
    imp.add_argument("--data", type=Path, default=ROOT / "data" / "udc-summary")
    imp.add_argument("--out", type=Path, default=ROOT / "data" / "pdc")
    chk = sub.add_parser("code", help="check PDC codes against the imported UDC Summary")
    chk.add_argument("codes", nargs="+")
    chk.add_argument("--out", type=Path, default=ROOT / "data" / "pdc")
    args = parser.parse_args(argv)

    if args.command == "import":
        try:
            stale = importer.write(args.data, args.out, check=args.check)
        except importer.ImportError_ as e:
            print(f"pdc import: {e}", file=sys.stderr)
            return 1
        for path in stale:
            print(f"stale: {path} (run `make import`)", file=sys.stderr)
        return 1 if stale else 0

    udc = _udc_notations(args.out)
    failed = False
    for c in args.codes:
        found = code.problems(c, udc)
        if found:
            failed = True
            for p in found:
                print(f"{c}: {p}", file=sys.stderr)
        else:
            parent = code.broader(c)
            print(f"{c}\tok" + (f"\tbroader {parent}" if parent else "\tUDC Summary class"))
    return 1 if failed else 0
