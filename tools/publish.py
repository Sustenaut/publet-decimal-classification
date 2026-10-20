#!/usr/bin/env python3
"""Sign the imported classes into the publet workspace of a signing key.

    tools/publish.py --key=DIR/.publet --created=YYYY-MM-DDTHH:MM:SSZ [--limit=N]

Composes each class in `data/pdc/udc-summary.json` as a `definitional`
claim with `pub compose`, files one `classifies` annotation per broader
link, placing each class under its broader classes (spec Section 9.1),
and signs every object it made with the key, for the purpose `authored`.

`--key` is the `.publet` directory holding the signing key, made with
`pub init` and `pub sign --generate-key --principal=... --label=...`; the
objects go into that workspace. Nothing here makes a key or picks a date:
`--created` is stated, never defaulted, so a signing run says when it
happened. Runs the `pub` found on PATH, which must know the `concept` sort
(publet spec Section 5.9.1, schryer/publet#49); to use another build, put
its directory first on PATH (`PATH=DIR:$PATH tools/publish.py ...`).
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PURPOSE = "authored"
TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


def run(pub: str, workspace: Path, *args: str) -> str:
    out = subprocess.run([pub, *args], cwd=workspace, capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"pub {' '.join(args[:2])}: {out.stderr.strip()}")
    return out.stdout.split()[0] if out.stdout.split() else ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--key", type=Path, required=True,
                        help="the .publet directory holding signing.key")
    parser.add_argument("--created", required=True,
                        help="the signing run's time, e.g. 2026-10-15T09:00:00Z")
    parser.add_argument("--limit", type=int, default=0, help="only the first N classes")
    args = parser.parse_args()
    if not TIMESTAMP.fullmatch(args.created):
        sys.exit(f"--created must be a UTC time such as 2026-10-15T09:00:00Z, not {args.created!r}")
    if args.key.name != ".publet" or not (args.key / "signing.key").is_file():
        sys.exit(f"{args.key} is not a .publet directory holding signing.key; "
                 "make one with `pub init` and `pub sign --generate-key`")
    pub = shutil.which("pub")
    if pub is None:
        sys.exit("no `pub` on PATH; put the directory holding it first on PATH")
    workspace = args.key.parent
    created = f"--created={args.created}"

    classes = json.loads((ROOT / "data" / "pdc" / "udc-summary.json").read_text())["classes"]
    if args.limit:
        classes = classes[: args.limit]
    cids: dict[str, str] = {}
    made: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        for c in classes:
            claim = c["claim"]
            defines = Path(tmp) / "defines.json"
            defines.write_text(json.dumps(claim["defines"]))
            cids[c["pdc"]] = run(
                pub, workspace, "compose", created,
                f"--class={claim['class']}", f"--lang={claim['lang']}",
                f"--content={claim['content']}", f"--scope={claim['scope']}",
                f"--defines={defines}", f"--cite={claim['cite']}",
                f"--cite-note={claim['cite_note']}",
            )
            made.append(cids[c["pdc"]])
    for c in classes:
        for parent in c["broader"]:
            if parent in cids:
                made.append(run(
                    pub, workspace, "annotate", created, "--kind=classifies",
                    f"--target={cids[c['pdc']]}", f"--subject={cids[parent]}",
                    "--scope=unconditional"))
    for cid in made:
        run(pub, workspace, "sign", created, f"--purpose={PURPOSE}", f"--target={cid}")
    (workspace / "pdc-cids.json").write_text(json.dumps(cids, indent=1, sort_keys=True) + "\n")
    print(f"{len(cids)} classes composed, {len(made) - len(cids)} placements, "
          f"{len(made)} objects signed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
