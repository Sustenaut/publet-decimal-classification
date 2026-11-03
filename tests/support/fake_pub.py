#!/usr/bin/env python3
"""A stand-in for publet's `pub`, `pub-cat`, `pub-store` and `pub-ls`.

`tools/publish.py` drives the real commands, which CI for a Python repository
does not install. This does just enough of what each does for that script to
run end to end: it composes by naming each object after its body, writes those
objects on `pub publish`, and logs every call to `FAKE_PUB_LOG`, so a test can
check what was asked of `pub` and in what order. It checks nothing a real `pub`
would, so the real thing is tested separately, where it is installed.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path


def cid(data: bytes) -> str:
    return "pub:sha2-256:" + hashlib.sha256(data).hexdigest()


def flag(args: list[str], name: str) -> str | None:
    return next((a.split("=", 1)[1] for a in args if a.startswith(f"--{name}=")), None)


def main() -> int:
    tool = Path(sys.argv[0]).name
    args = sys.argv[1:]
    with open(os.environ["FAKE_PUB_LOG"], "a") as log:
        log.write(json.dumps({"tool": tool, "args": args, "cwd": os.getcwd()}) + "\n")
    here = Path.cwd()
    made = here / ".publet" / "made"
    if tool == "pub-cat":
        sys.stdout.write("a key object")
    elif tool == "pub-store":
        print(cid(sys.stdin.buffer.read()))
    elif tool == "pub-ls":
        return 0
    elif args[:2] == ["corpus", "init"]:
        (here / ".publet").mkdir()
        (here / ".publet" / "config").write_text(
            "author=pub:sha2-256:placeholder\npolicy=pub:sha2-256:initpolicy\n")
        (here / "corpus.json").write_text("{}\n")
    elif args[:1] == ["compose"]:
        body = Path(flag(args, "defines")).read_bytes()
        name = cid(body)
        made.mkdir(exist_ok=True)
        (made / name.replace(":", "_")).write_bytes(body)
        print(name)
    elif args[:1] == ["publish"]:
        objects = here / "objects"
        objects.mkdir(exist_ok=True)
        for path in made.iterdir():
            (objects / (path.name + ".cbor")).write_bytes(path.read_bytes())
        print("generation 0  pub:sha2-256:generation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
