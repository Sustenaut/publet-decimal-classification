"""The PDC's own steps; running `pdc` and `tools/publish.py`, the scratch
files and the checks of what they did are pubtest's (GRAMMAR.md)."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/codes.feature", "../features/import.feature", "../features/install.feature")

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import pdc  # noqa: E402
from pdc import families as grouping  # noqa: E402


def _pyproject_version() -> str:
    return tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]


def _repository_json(*parts: str):
    return json.loads(ROOT.joinpath(*parts).read_text())


@then('it prints its name, "pdc", and the version in pyproject.toml')
def prints_version(result):
    assert result.stdout == f"pdc {_pyproject_version()}\n", result.stdout


# --- the committed import ----------------------------------------------------


def _classes_of(family: dict) -> list[dict]:
    return family["defines"]["members"] + family["defines"].get("auxiliaries", [])


def _families() -> dict:
    return _repository_json("data", "pdc", "families.json")


def _family_under(parent: str | None, data: dict | None = None) -> dict:
    return next(f for f in (data or _families())["families"] if f["defines"].get("parent") == parent)


@when("I read the committed import")
def read_import(ctx):
    ctx.attempt(lambda: {"classes": _repository_json("data", "pdc", "udc-summary.json")["classes"],
                         "families": _families(), "cids": _repository_json("data", "pdc", "cids.json")})


@when(parsers.parse('I look up the concept "{code}" in the families'))
def concept(ctx, code):
    ctx.attempt(lambda: next(m for f in _families()["families"] for m in _classes_of(f) if m["pdc"] == code))


@when(parsers.parse('I look up the class "{code}" in the import'))
def imported(ctx, code):
    ctx.attempt(lambda: next(c for c in _repository_json("data", "pdc", "udc-summary.json")["classes"]
                             if c["pdc"] == code))


@when("I list the families")
def list_families(ctx):
    ctx.attempt(lambda: _families()["families"])


@when("I list the members of the top family")
def top_members(ctx):
    ctx.attempt(lambda: [m["pdc"] for m in _family_under(None)["defines"]["members"]])


@when(parsers.parse('I list the {kind} of the family under "{parent}"'))
def list_kind(ctx, kind, parent):
    ctx.attempt(lambda: [m["pdc"] for m in _family_under(parent)["defines"][kind]])


@when(parsers.parse('I look up the family under "{parent}"'))
def family_under(ctx, parent):
    ctx.attempt(lambda: _family_under(parent))


@when(parsers.parse("I look up group {number:d}"))
def group(ctx, number):
    ctx.attempt(lambda: next(g for g in _families()["groups"] if g["number"] == number))


@when("I group a class with two broader classes into families")
def two_broader(ctx):
    ctx.attempt(lambda: grouping.build([{"pdc": "1", "uri": "u", "name": "n", "broader": ["a", "b"]}]))


STEWARD = "pub:sha2-256:ue7bjgletvpfendw4dptudm64oaaqaoia3pu7vnao6xq6fq5o6jq"


def _object(cid: str) -> Path:
    return ROOT / "corpus" / "objects" / f"{cid.replace(':', '_')}.cbor"


def _digest(cid: str) -> bytes:
    tail = cid.rsplit(":", 1)[1].upper()
    return base64.b32decode(tail + "=" * (-len(tail) % 8))


def _verified(cid: str) -> bytes:
    body = _object(cid).read_bytes()
    assert hashlib.sha256(body).digest() == _digest(cid), cid
    return body


@then("every imported class is defined by its family's object in corpus/objects/, under the CID in "
      "data/pdc/cids.json")
def every_class_signed(ctx):
    classes = ctx.result["cids"]["classes"]
    assert set(classes) == {c["pdc"] for c in ctx.result["classes"]}
    bodies = {cid: _verified(cid) for cid in set(classes.values())}
    for code, cid in classes.items():
        assert b"family" in bodies[cid] and code.encode() in bodies[cid], code


@then("the edition in data/pdc/cids.json is in corpus/objects/ and lists every family there")
def edition_signed(ctx):
    cids = ctx.result["cids"]
    body = _verified(cids["edition"])
    assert b"edition" in body
    for family in set(cids["classes"].values()):
        assert family.encode() in body, family


@then("corpus/objects/ holds the PDC steward key's public key object")
def steward_key():
    body = _object(STEWARD).read_bytes()
    assert hashlib.sha256(body).digest() == _digest(STEWARD)
    assert b"PDC steward key" in body and b"signing" not in body


@then("every imported class is in exactly one family, the one under its broader class")
def one_family_each(ctx):
    seen = {}
    for family in ctx.result["families"]["families"]:
        for member in _classes_of(family):
            assert member["pdc"] not in seen, member["pdc"]
            seen[member["pdc"]] = family["defines"].get("parent")
    classes = ctx.result["classes"]
    assert set(seen) == {c["pdc"] for c in classes}
    for c in classes:
        assert seen[c["pdc"]] == (c["broader"][0] if c["broader"] else None), c["pdc"]


@then("each class has `children` exactly when a family lists it as its parent")
def children_flags(ctx):
    data = ctx.result["families"]["families"]
    parents = {f["defines"]["parent"] for f in data if "parent" in f["defines"]}
    for family in data:
        for member in _classes_of(family):
            assert member.get("children", False) == (member["pdc"] in parents), member["pdc"]
            assert member.get("children", True) is True, member["pdc"]


def _group_of(data: dict, head: str) -> int:
    return next(g["number"] for g in data["groups"] if head in g["heads"])


def _groups_of_family(data: dict, parent: str) -> set[int]:
    number = _family_under(parent, data)["defines"]["grouping"]
    return set(next(g["groups"] for g in data["groupings"] if g["number"] == number))


@then(parsers.parse('group 1 holds the members of the family under "{parent}"'))
def common_group(ctx, parent):
    data = ctx.result["families"]
    assert data["groups"][0] == {
        "number": 1, "heads": sorted(m["pdc"] for m in _family_under(parent, data)["defines"]["members"])}


@then(parsers.parse('the grouping of the family under "{parent}" is the common group and that of "{head}"'))
def grouping_of(ctx, parent, head):
    data = ctx.result["families"]
    assert _groups_of_family(data, parent) == {1, _group_of(data, head)}


@then(parsers.parse('the grouping of the family under "{parent}" adds those of "{head}" to the common group'))
def grouping_adds(ctx, parent, head):
    data = ctx.result["families"]
    groups = _groups_of_family(data, parent)
    assert 1 in groups and _group_of(data, head) in groups, groups


@then("every family's grouping is defined, and every grouping's groups are")
def groupings_defined(ctx):
    data = ctx.result["families"]
    groups = {g["number"] for g in data["groups"]}
    groupings = {g["number"]: g["groups"] for g in data["groupings"]}
    for family in data["families"]:
        assert family["defines"]["grouping"] in groupings, family["defines"].get("parent")
    assert all(set(g) <= groups for g in groupings.values())


@then("the counts in families.json agree with the families")
def counts_agree(ctx):
    data = ctx.result["families"]
    tally = {}
    for family in data["families"]:
        for name in (family["section"], "total"):
            if name:
                t = tally.setdefault(name, {"families": 0, "classes": 0, "auxiliaries": 0})
                t["families"] += 1
                t["classes"] += len(family["defines"]["members"])
                t["auxiliaries"] += len(family["defines"].get("auxiliaries", []))
    counts = data["counts"]
    assert {k: counts[k] for k in tally} == tally
    assert counts["groups"] == len(data["groups"]) and counts["groupings"] == len(data["groupings"])
    assert counts["total"]["classes"] + counts["total"]["auxiliaries"] == 2430


# --- importing a changed source ----------------------------------------------


@given(parsers.parse('in the file "{path}", "{old}" is replaced by "{new}"'))
def replaced(ctx, path, old, new):
    target = ctx.directory / path
    text = target.read_text()
    assert old in text, f"{path} does not hold {old!r}"
    target.write_text(text.replace(old, new))


@given(parsers.parse('the source in "{path}" is pinned as it stands'))
def repinned(ctx, path):
    data = ctx.directory / path
    source = json.loads((data / "source.json").read_text())
    source["sha256"] = hashlib.sha256((data / source["file"]).read_bytes()).hexdigest()
    (data / "source.json").write_text(json.dumps(source))


@given(parsers.parse('a file "{path}" holding the committed families with the group numbers reversed'))
def reversed_numbers(ctx, path):
    data = _families()
    numbers = [g["number"] for g in data["groups"]][1:]
    for item, number in zip(data["groups"][1:], reversed(numbers)):
        item["number"] = number
    target = ctx.directory / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False))
    ctx.expected = {g["heads"][0]: g["number"] for g in data["groups"][1:]}


@then(parsers.parse('each head in "{path}" keeps its reversed number'))
def numbers_kept(ctx, path):
    data = json.loads((ctx.directory / path).read_text())
    assert {g["heads"][0]: g["number"] for g in data["groups"][1:]} == ctx.expected


# --- the installed package -----------------------------------------------------


@when("I ask the package for its edition")
def package_edition(ctx):
    ctx.attempt(pdc.edition)


@when("I ask the package for every code's family")
def package_cids(ctx):
    ctx.attempt(pdc.cids)


@when("I ask the package for its classes")
def package_classes(ctx):
    ctx.attempt(pdc.classes)


@when("I ask the package for its families")
def package_families(ctx):
    ctx.attempt(lambda: pdc.family_data()["families"])


@then(parsers.parse('the result is what the JSON in "{path}" has at "{key}"'))
def result_is_json_at(ctx, path, key):
    from pubtest.core import dig
    wanted = dig(json.loads((ctx.directory / path).read_text()), key)
    assert ctx.result == wanted, ctx.result


@given("the package installed with pip into a fresh environment, first on PATH")
def installed(ctx, tmp_path_factory, monkeypatch):
    env = tmp_path_factory.mktemp("venv")
    subprocess.run([sys.executable, "-m", "venv", str(env)], check=True)
    subprocess.run([str(env / "bin" / "pip"), "install", "--quiet", str(ROOT)], check=True)
    monkeypatch.setenv("PATH", f"{env / 'bin'}{os.pathsep}{os.environ['PATH']}")
    ctx.env = env


@then("the installed package reads every imported class and its CID from its own data")
def installed_data(ctx):
    script = ("import json, pdc; d = pdc.data_dir(); "
              "print(json.dumps([str(d), len(pdc.classes()), sorted(pdc.cids()) == sorted(c['pdc'] for c in pdc.classes())]))")
    out = subprocess.run([str(ctx.env / "bin" / "python"), "-c", script],
                         capture_output=True, text=True, cwd=ctx.directory, check=True).stdout
    where, count, same = json.loads(out)
    assert Path(where).is_relative_to(ctx.env), where
    expected = _repository_json("data", "pdc", "udc-summary.json")["classes"]
    assert count == len(expected) and same, out


@then("the installed pdc names the version in pyproject.toml")
def installed_version(ctx):
    out = subprocess.run([str(ctx.env / "bin" / "pdc"), "--version"],
                         capture_output=True, text=True, cwd=ctx.directory, check=True).stdout
    assert out == f"pdc {_pyproject_version()}\n", out


# --- publishing, with a stand-in pub ---------------------------------------

FAKE = Path(__file__).resolve().parent.parent / "support" / "fake_pub.py"


@given(parsers.parse('a key directory "{path}"'))
def key_directory(ctx, path):
    key = ctx.directory / path
    key.mkdir(parents=True)
    (key / "signing.key").write_text("00" * 32 + "\n")
    (key / "config").write_text("author=pub:sha2-256:steward\n")


@given("a stand-in pub that composes what it is given")
def standin_pub(ctx, tmp_path, monkeypatch):
    """`pub` and its plumbing as one stand-in (tests/support/fake_pub.py),
    first on PATH, which names each object it composes after its body and
    logs every call with its directory."""
    bin_dir = tmp_path / "fake-pub"
    bin_dir.mkdir()
    for tool in ("pub", "pub-cat", "pub-store", "pub-ls"):
        (bin_dir / tool).symlink_to(FAKE)
    ctx.pub_log = tmp_path / "pub.log"
    ctx.pub_log.write_text("")
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_PUB_LOG", str(ctx.pub_log))


@given(parsers.parse('no directory on PATH holds "{name}"'))
def no_program(monkeypatch, name):
    monkeypatch.setenv("PATH", os.pathsep.join(p for p in os.environ["PATH"].split(os.pathsep)
                                               if not (Path(p) / name).exists()))


def _calls(ctx) -> list[dict]:
    return [json.loads(line) for line in ctx.pub_log.read_text().splitlines()]


@then(parsers.parse('the stand-in composed every family and then the edition, each signed with '
                    'purpose "{purpose}"'))
def composed_in_order(ctx, purpose):
    calls = _calls(ctx)
    composes = [c for c in calls if c["args"][:1] == ["compose"]]
    signs = [c for c in calls if c["args"][:1] == ["sign"]]
    assert len(composes) == 574 and len(signs) == 574, (len(composes), len(signs))
    assert all(f"--purpose={purpose}" in c["args"] for c in signs)
    made = ctx.directory / "new" / ".publet" / "made"
    sorts = [json.loads(p.read_text())["sort"] for p in made.iterdir()]
    assert sorts.count("family") == 573 and sorts.count("edition") == 1
    last = next(a for a in composes[-1]["args"] if a.startswith("--content="))
    assert last == "--content=The PDC at release 0.2.0.", last


@then(parsers.parse('the stand-in\'s edition lists every family composed, and "{path}" names it and every code'))
def standin_edition_lists(ctx, path):
    target = ctx.directory / path
    cids = json.loads(target.read_text())
    edition = json.loads((target.parent / "objects" / (cids["edition"].replace(":", "_") + ".cbor")).read_text())
    listed = {edition["top"], *(c for s in edition["sections"].values() for c in s.values())}
    assert listed == set(cids["classes"].values()) and len(listed) == 573
    classes = _repository_json("data", "pdc", "udc-summary.json")["classes"]
    assert set(cids["classes"]) == {c["pdc"] for c in classes}


@then("the stand-in was asked to publish only after the pin was checked in the repository")
def pin_first(ctx):
    calls = _calls(ctx)
    require = next(i for i, c in enumerate(calls) if c["args"][:1] == ["require"])
    publish = next(i for i, c in enumerate(calls) if c["args"][:1] == ["publish"])
    assert require < publish and calls[require]["cwd"] == str(ROOT)


@then("the stand-in composed nothing")
def nothing_composed(ctx):
    calls = _calls(ctx)
    assert not [c for c in calls if c["args"][:1] in (["compose"], ["corpus"])], calls


# --- publishing, with a throwaway key --------------------------------------


def _held(key: Path) -> str:
    return subprocess.run(["pub-store", f"--store={key / 'objects.redb'}", "list"],
                          capture_output=True, text=True, check=True).stdout


@given(parsers.parse('a throwaway key "{path}" made by a pub that knows families'))
def throwaway(ctx, monkeypatch, path):
    """A `pub` that knows families, from PUB_BIN_DIR, first on PATH."""
    bin_dir = os.environ.get("PUB_BIN_DIR")
    if not bin_dir:
        pytest.skip("PUB_BIN_DIR names no directory holding a pub that knows families")
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    key = ctx.directory / path
    key.parent.mkdir(parents=True)
    for args in (["init"], ["sign", "--generate-key", "--principal=human", "--label=throwaway"]):
        subprocess.run(["pub", *args], cwd=key.parent, check=True, capture_output=True)
    ctx.key, ctx.held = key, _held(key)


@then(parsers.parse('the edition of the corpus "{path}" lists every family by its CID'))
def edition_lists(ctx, path):
    corpus = ctx.directory / path
    cids = json.loads((corpus / "pdc-cids.json").read_text())
    subprocess.run(["pub", "bundle", "--dir=objects", "--out=bundles"], cwd=corpus, check=True,
                   capture_output=True)
    edition = json.loads((corpus / "bundles" / "o" / f"{cids['edition']}.json").read_text())
    defines = edition["object"]["body"]["defines"]
    listed = {defines["top"], *(c for s in defines["sections"].values() for c in s.values())}
    assert listed == set(cids["classes"].values()) and len(listed) == 573


@then("the key's store is unchanged")
def store_unchanged(ctx):
    assert _held(ctx.key) == ctx.held
