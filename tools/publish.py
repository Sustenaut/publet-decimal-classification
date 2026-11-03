#!/usr/bin/env python3
"""Compose the PDC's families and edition into a fresh corpus, signed by a key.

    tools/publish.py --key=DIR/.publet --corpus=NEW --release=X.Y.Z \\
                     --created=YYYY-MM-DDTHH:MM:SSZ

Composes each family in `data/pdc/families.json` as a `definitional` claim
with `pub compose`, then the edition listing them all (publet spec Section
5.9.1), and signs every one with the key for the purpose `authored`. It then
runs `pub publish`, which signs the package publet, exports `objects/` and
writes a new domain at generation 0 with its signed generation record.

`--corpus` must not exist: the families start a new domain, because a generation
may not lose members, and the concept objects before them stay in git history.
`--key` is the `.publet` directory holding the signing key, made with `pub init`
and `pub sign --generate-key --principal=... --label=...`. Nothing is added to
its store, and the secret is reached through a link in the
new corpus that is removed at the end, so the secret is not copied. `--created`
is stated, never defaulted, so a signing run says when it happened.

Runs the `pub`, `pub-cat`, `pub-store` and `pub-ls` found on PATH: a release of
publet that `pub-version.txt` admits, which is checked first. Install it with
`cargo install --locked --git https://github.com/Sustenaut/publet --tag v0.3.0
publet-cli pub-ls pub-cat pub-store`.
Prints the numbers, and writes `pdc-cids.json` in the corpus: the edition's CID,
and each code's family CID.
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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pdc import families as grouping  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PURPOSE = "authored"
TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
OBJECT_LIMIT = 1024 * 1024
PACKAGE = "publets/pkg.publet-decimal-classification"


def run(workspace: Path, *argv: str, stdin: bytes | None = None) -> bytes:
    out = subprocess.run(argv, cwd=workspace, capture_output=True, input=stdin)
    if out.returncode != 0:
        sys.exit(f"{' '.join(argv[:2])}: {out.stderr.decode().strip()}")
    return out.stdout


def first_word(output: bytes) -> str:
    words = output.decode().split()
    return words[0] if words else ""


def compose(workspace: Path, tmp: Path, created: str, content: str, defines: dict,
            data: dict) -> str:
    path = tmp / "defines.json"
    path.write_text(json.dumps(defines, ensure_ascii=False))
    cid = first_word(run(
        workspace, "pub", "compose", created, "--class=definitional", "--lang=en",
        f"--content={content}", "--scope=unconditional", f"--defines={path}",
        f"--cite={data['cite']}", f"--cite-note={data['cite_note']}",
    ))
    run(workspace, "pub", "sign", created, f"--purpose={PURPOSE}", f"--target={cid}")
    return cid


def adopt_key(key: Path, corpus: Path) -> None:
    """Make the key this corpus's, by a link to its secret and a copy of its
    public key object."""
    author = next(line.split("=", 1)[1] for line in (key / "config").read_text().splitlines()
                  if line.startswith("author="))
    public = run(corpus, "pub-cat", f"--store={key / 'objects.redb'}", author)
    run(corpus, "pub-store", "--store=.publet/objects.redb", "add", stdin=public)
    config = corpus / ".publet" / "config"
    config.write_text("".join(f"author={author}\n" if line.startswith("author=") else line + "\n"
                              for line in config.read_text().splitlines()))
    (corpus / ".publet" / "signing.key").symlink_to((key / "signing.key").resolve())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--key", type=Path, required=True,
                        help="the .publet directory holding signing.key")
    parser.add_argument("--corpus", type=Path, required=True,
                        help="the new corpus's directory, which must not exist")
    parser.add_argument("--release", required=True, help="the PDC release this edition is")
    parser.add_argument("--created", required=True,
                        help="the signing run's time, e.g. 2026-10-15T09:00:00Z")
    args = parser.parse_args()
    if not TIMESTAMP.fullmatch(args.created):
        sys.exit(f"--created must be a UTC time such as 2026-10-15T09:00:00Z, not {args.created!r}")
    if args.key.name != ".publet" or not (args.key / "signing.key").is_file():
        sys.exit(f"{args.key} is not a .publet directory holding signing.key; "
                 "make one with `pub init` and `pub sign --generate-key`")
    if args.corpus.exists():
        sys.exit(f"{args.corpus} exists; the families start a new corpus")
    for tool in ("pub", "pub-cat", "pub-store", "pub-ls"):
        if shutil.which(tool) is None:
            sys.exit(f"no `{tool}` on PATH; put the directory holding it first on PATH")
    pinned = subprocess.run(["pub", "require"], cwd=ROOT, capture_output=True, text=True)
    if pinned.returncode != 0:
        sys.exit(pinned.stderr.strip() or "the pub on PATH is not the one pub-version.txt names")
    created = f"--created={args.created}"
    data = json.loads((ROOT / "data" / "pdc" / "families.json").read_text())
    config = json.loads((ROOT / "corpus" / "corpus.json").read_text())

    corpus = args.corpus
    corpus.mkdir(parents=True)
    run(corpus, "pub", "corpus", "init", "--name=corpus", f"--label={config['label']}",
        f"--bound={config['bound']}")
    adopt_key(args.key.resolve(), corpus)
    shutil.copytree(ROOT / "corpus" / PACKAGE, corpus / PACKAGE)

    cids: dict[str | None, str] = {}
    classes: dict[str, str] = {}
    with tempfile.TemporaryDirectory() as tmp:
        for family in data["families"]:
            defines = family["defines"]
            cid = compose(corpus, Path(tmp), created, family["content"], defines, data)
            cids[defines.get("parent")] = cid
            for member in defines["members"] + defines.get("auxiliaries", []):
                classes[member["pdc"]] = cid
        edition_cid = compose(corpus, Path(tmp), created,
                              f"The PDC at release {args.release}.",
                              grouping.edition(data, cids), data)

    run(corpus, "pub", "build")
    published = run(corpus, "pub", "publish", "--all", "--no-rendering").decode()
    (corpus / ".publet" / "signing.key").unlink()
    check = subprocess.run(["pub-ls", "--dir=objects"], cwd=corpus, capture_output=True, text=True)
    if check.returncode != 0 or "warning" in check.stderr:
        sys.exit(f"the corpus does not load cleanly: {check.stderr.strip()}")

    (corpus / "pdc-cids.json").write_text(json.dumps(
        {"edition": edition_cid, "classes": classes}, ensure_ascii=False, indent=1, sort_keys=True,
    ) + "\n")
    edition_size = (corpus / "objects" / (edition_cid.replace(":", "_") + ".cbor")).stat().st_size
    if edition_size > OBJECT_LIMIT:
        sys.exit(f"the edition is {edition_size} bytes, over the {OBJECT_LIMIT} byte object limit")
    objects = sorted((corpus / "objects").glob("*.cbor"))
    largest = max(p.stat().st_size for p in objects)
    print(f"{len(cids)} families, {len(classes)} codes, {len(data['groups'])} groups, "
          f"{len(data['groupings'])} groupings")
    print(f"edition {edition_cid}, {edition_size} bytes")
    print(f"{len(objects)} objects in all, the largest {largest} bytes, "
          f"{sum(p.stat().st_size for p in objects)} bytes in total")
    print(published.strip().splitlines()[-1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
