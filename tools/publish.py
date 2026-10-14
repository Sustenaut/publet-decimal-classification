#!/usr/bin/env python3
"""Sign the imported classes into a publet workspace.

    tools/publish.py --pub=PATH --workspace=DIR [--limit=N]

Composes each class in `data/pdc/udc-summary.json` as a `definitional`
claim with `pub compose`, then files one `classifies` annotation per
broader link, placing each class under its broader classes (spec Section
9.1). The key is the workspace's own: run `pub init` in it first, or let
this do it. Needs a `pub` that knows the `concept` sort (publet spec
Section 5.9.1, schryer/publet#49).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(pub: str, workspace: Path, *args: str) -> str:
    out = subprocess.run([pub, *args], cwd=workspace, capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"pub {' '.join(args[:2])}: {out.stderr.strip()}")
    return out.stdout.split()[0] if out.stdout.split() else ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pub", required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=0, help="only the first N classes")
    args = parser.parse_args()
    args.workspace.mkdir(parents=True, exist_ok=True)
    if not (args.workspace / ".publet").exists():
        run(args.pub, args.workspace, "init")
    classes = json.loads((ROOT / "data" / "pdc" / "udc-summary.json").read_text())["classes"]
    if args.limit:
        classes = classes[: args.limit]
    cids: dict[str, str] = {}
    with tempfile.TemporaryDirectory() as tmp:
        for c in classes:
            claim = c["claim"]
            defines = Path(tmp) / "defines.json"
            defines.write_text(json.dumps(claim["defines"]))
            cids[c["pdc"]] = run(
                args.pub, args.workspace, "compose",
                f"--class={claim['class']}", f"--lang={claim['lang']}",
                f"--content={claim['content']}", f"--scope={claim['scope']}",
                f"--defines={defines}", f"--cite={claim['cite']}",
                f"--cite-note={claim['cite_note']}",
            )
    placed = 0
    for c in classes:
        for parent in c["broader"]:
            if parent in cids:
                run(args.pub, args.workspace, "annotate", "--kind=classifies",
                    f"--target={cids[c['pdc']]}", f"--subject={cids[parent]}",
                    "--scope=unconditional")
                placed += 1
    (args.workspace / "pdc-cids.json").write_text(json.dumps(cids, indent=1, sort_keys=True) + "\n")
    print(f"{len(cids)} classes composed, {placed} placed under a broader class")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
