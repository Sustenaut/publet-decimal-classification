"""Steps driving `bin/pdc` as a user would, from PDC_BIN_DIR."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/codes.feature", "../features/import.feature", "../features/install.feature")

ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def pdc() -> Path:
    raw = os.environ.get("PDC_BIN_DIR")
    if not raw:
        pytest.fail("PDC_BIN_DIR is not set; run the suite through `make functional`")
    return Path(raw) / "pdc"


@pytest.fixture
def ctx() -> dict:
    return {}


def _run(pdc: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([str(pdc), *args], capture_output=True, text=True)


@when(parsers.parse('I check the code "{code}"'), target_fixture="result")
def check_code(pdc, code: str):
    return _run(pdc, "code", code)


@when("I ask pdc for its version", target_fixture="result")
def ask_version(pdc):
    return _run(pdc, "--version")


def _pyproject_version() -> str:
    import tomllib
    return tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]


@then('stdout is "pdc" and the version in pyproject.toml')
def stdout_version(result):
    assert result.stdout == f"pdc {_pyproject_version()}\n", result.stdout


@when("I check the import", target_fixture="result")
def check_import(pdc):
    return _run(pdc, "import", "--check")


@then("it succeeds")
def succeeds(result):
    assert result.returncode == 0, result.stderr


@then("it fails")
def fails(result):
    assert result.returncode != 0, result.stdout


@then(parsers.parse('stdout says "{text}"'))
def stdout_says(result, text: str):
    assert text.replace("\\t", "\t") in result.stdout, result.stdout


@then(parsers.parse('stderr says "{text}"'))
def stderr_says(result, text: str):
    assert text in result.stderr, result.stderr


def _imported(code: str) -> dict:
    data = json.loads((ROOT / "data" / "pdc" / "udc-summary.json").read_text())
    return next(c for c in data["classes"] if c["pdc"] == code)


def _families() -> dict:
    return json.loads((ROOT / "data" / "pdc" / "families.json").read_text())


def _classes_of(family: dict) -> list[dict]:
    return family["defines"]["members"] + family["defines"].get("auxiliaries", [])


def _family_defining(code: str) -> dict:
    return next(f for f in _families()["families"]
                if any(m["pdc"] == code for m in _classes_of(f)))


def _family_under(parent: str | None) -> dict:
    return next(f for f in _families()["families"] if f["defines"].get("parent") == parent)


def _member(code: str) -> dict:
    return next(m for m in _classes_of(_family_defining(code)) if m["pdc"] == code)


@then(parsers.parse('the imported class "{code}" is a concept named "{name}"'))
def concept_named(code: str, name: str):
    member = _member(code)
    assert member["name"] == name, member
    assert "sort" not in member and "kind" not in member and "relation" not in member, member


@then(parsers.parse('the imported class "{code}" matches "{prefix}"'))
def concept_matches(code: str, prefix: str):
    matches = _member(code)["matches"]
    assert matches[0]["ref"].startswith(prefix), matches


@then(parsers.parse('the imported class "{code}" is under "{parent}"'))
def concept_under(code: str, parent: str):
    assert parent in _imported(code)["broader"]


STEWARD = "pub:sha2-256:ue7bjgletvpfendw4dptudm64oaaqaoia3pu7vnao6xq6fq5o6jq"


def _object(cid: str) -> Path:
    return ROOT / "corpus" / "objects" / f"{cid.replace(':', '_')}.cbor"


def _cids() -> dict:
    return json.loads((ROOT / "data" / "pdc" / "cids.json").read_text())


def _verified(cid: str) -> bytes:
    body = _object(cid).read_bytes()
    assert hashlib.sha256(body).digest() == _digest(cid), cid
    return body


@then("every imported class is defined by its family's object in corpus/objects/, under the CID in "
      "data/pdc/cids.json")
def every_class_signed():
    data = json.loads((ROOT / "data" / "pdc" / "udc-summary.json").read_text())
    classes = _cids()["classes"]
    assert set(classes) == {c["pdc"] for c in data["classes"]}
    bodies = {cid: _verified(cid) for cid in set(classes.values())}
    for code, cid in classes.items():
        assert b"family" in bodies[cid] and code.encode() in bodies[cid], code


@then("the edition in data/pdc/cids.json is in corpus/objects/ and lists every family there")
def edition_signed():
    cids = _cids()
    body = _verified(cids["edition"])
    assert b"edition" in body
    for family in set(cids["classes"].values()):
        assert family.encode() in body, family


def _digest(cid: str) -> bytes:
    import base64
    tail = cid.rsplit(":", 1)[1].upper()
    return base64.b32decode(tail + "=" * (-len(tail) % 8))


@then("corpus/objects/ holds the PDC steward key's public key object")
def steward_key():
    body = _object(STEWARD).read_bytes()
    assert hashlib.sha256(body).digest() == _digest(STEWARD)
    assert b"PDC steward key" in body and b"signing" not in body


def _copy(tmp_path: Path) -> Path:
    data = tmp_path / "udc-summary"
    shutil.copytree(ROOT / "data" / "udc-summary", data)
    return data


def _repin(data: Path) -> None:
    source = json.loads((data / "source.json").read_text())
    source["sha256"] = hashlib.sha256((data / source["file"]).read_bytes()).hexdigest()
    (data / "source.json").write_text(json.dumps(source))


@given("a copy of the source with one class relabelled")
def relabelled(tmp_path, ctx):
    data = _copy(tmp_path)
    ttl = data / "udcs.ttl"
    ttl.write_text(ttl.read_text().replace('"Agriculture in general"@en', '"Farming"@en'))
    ctx["data"] = data


@given(parsers.parse('a copy of the source with the notation "{notation}" pinned as it stands'))
def separator_in_notation(tmp_path, ctx, notation: str):
    data = _copy(tmp_path)
    ttl = data / "udcs.ttl"
    ttl.write_text(ttl.read_text().replace('skos:notation "631"^^', f'skos:notation "{notation}"^^'))
    _repin(data)
    ctx["data"] = data


@when("I import the copy", target_fixture="result")
def import_copy(pdc, ctx, tmp_path):
    return _run(pdc, "import", f"--data={ctx['data']}", f"--out={tmp_path / 'out'}")


@given("the package installed with pip into a fresh environment", target_fixture="env")
def installed(tmp_path_factory) -> Path:
    env = tmp_path_factory.mktemp("venv")
    subprocess.run([sys.executable, "-m", "venv", str(env)], check=True)
    subprocess.run([str(env / "bin" / "pip"), "install", "--quiet", str(ROOT)], check=True)
    return env


@when(parsers.parse('I check the code "{code}" with the installed pdc'), target_fixture="result")
def check_code_installed(env, code: str, tmp_path):
    return subprocess.run([str(env / "bin" / "pdc"), "code", code],
                          capture_output=True, text=True, cwd=tmp_path)


@then("the installed package reads every imported class and its CID from its own data")
def installed_data(env, tmp_path):
    script = ("import json, pdc; d = pdc.data_dir(); "
              "print(json.dumps([str(d), len(pdc.classes()), sorted(pdc.cids()) == sorted(c['pdc'] for c in pdc.classes())]))")
    out = subprocess.run([str(env / "bin" / "python"), "-c", script],
                         capture_output=True, text=True, cwd=tmp_path, check=True).stdout
    where, count, same = json.loads(out)
    assert Path(where).is_relative_to(env), where
    expected = json.loads((ROOT / "data" / "pdc" / "udc-summary.json").read_text())["classes"]
    assert count == len(expected) and same, out


@then("the installed pdc names the version in pyproject.toml")
def installed_version(env, tmp_path):
    out = subprocess.run([str(env / "bin" / "pdc"), "--version"],
                         capture_output=True, text=True, cwd=tmp_path, check=True).stdout
    assert out == f"pdc {_pyproject_version()}\n", out


# --- families ----------------------------------------------------------------


@then("every imported class is in exactly one family, the one under its broader class")
def one_family_each():
    seen = {}
    for family in _families()["families"]:
        for member in _classes_of(family):
            assert member["pdc"] not in seen, member["pdc"]
            seen[member["pdc"]] = family["defines"].get("parent")
    data = json.loads((ROOT / "data" / "pdc" / "udc-summary.json").read_text())["classes"]
    assert set(seen) == {c["pdc"] for c in data}
    for c in data:
        assert seen[c["pdc"]] == (c["broader"][0] if c["broader"] else None), c["pdc"]


@then(parsers.parse('the top family holds "{first}" and "{second}"'))
def top_family(first: str, second: str):
    assert [m["pdc"] for m in _family_under(None)["defines"]["members"]] == [first, second]


@then(parsers.parse("there are {count:d} families"))
def family_count(count: int):
    assert len(_families()["families"]) == count


@then(parsers.parse('the family under "{parent}" lists "{aux}" as an auxiliary and "{member}" as a member'))
def auxiliary_apart(parent: str, aux: str, member: str):
    defines = _family_under(parent)["defines"]
    assert aux in [m["pdc"] for m in defines["auxiliaries"]], defines
    assert member in [m["pdc"] for m in defines["members"]], defines


@then(parsers.parse('the family under "{parent}" is in the section "{section}"'))
def family_section(parent: str, section: str):
    assert _family_under(parent)["section"] == section


@then("each class has `children` exactly when a family lists it as its parent")
def children_flags():
    data = _families()["families"]
    parents = {f["defines"]["parent"] for f in data if "parent" in f["defines"]}
    for family in data:
        for member in _classes_of(family):
            assert member.get("children", False) == (member["pdc"] in parents), member["pdc"]
            assert member.get("children", True) is True, member["pdc"]


def _group_of(head: str) -> int:
    return next(g["number"] for g in _families()["groups"] if head in g["heads"])


def _groups_of_family(parent: str) -> set[int]:
    data = _families()
    number = _family_under(parent)["defines"]["grouping"]
    return set(next(g["groups"] for g in data["groupings"] if g["number"] == number))


@then(parsers.parse('group 1 holds the six heads under "{parent}"'))
def common_group(parent: str):
    assert _families()["groups"][0] == {
        "number": 1, "heads": sorted(m["pdc"] for m in _family_under(parent)["defines"]["members"])}


@then(parsers.parse('the grouping of the family under "{parent}" is the common group and that of "{head}"'))
def grouping_of(parent: str, head: str):
    assert _groups_of_family(parent) == {1, _group_of(head)}


@then(parsers.parse('the grouping of the family under "{parent}" adds those of "{head}" to the common group'))
def grouping_adds(parent: str, head: str):
    groups = _groups_of_family(parent)
    assert 1 in groups and _group_of(head) in groups, groups


@then("every family's grouping is defined, and every grouping's groups are")
def groupings_defined():
    data = _families()
    groups = {g["number"] for g in data["groups"]}
    groupings = {g["number"]: g["groups"] for g in data["groupings"]}
    for family in data["families"]:
        assert family["defines"]["grouping"] in groupings, family["defines"].get("parent")
    assert all(set(g) <= groups for g in groupings.values())


@then("the counts in families.json agree with the families")
def counts_agree():
    data = _families()
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


@given("the families with the group numbers reversed")
def reversed_numbers(tmp_path, ctx):
    data = _families()
    numbers = [g["number"] for g in data["groups"]][1:]
    for group, number in zip(data["groups"][1:], reversed(numbers)):
        group["number"] = number
    out = tmp_path / "out"
    out.mkdir()
    (out / "families.json").write_text(json.dumps(data, ensure_ascii=False))
    ctx["out"] = out
    ctx["expected"] = {g["heads"][0]: g["number"] for g in data["groups"][1:]}


@when("I import over them", target_fixture="result")
def import_over(pdc, ctx):
    return _run(pdc, "import", f"--out={ctx['out']}")


@then("each head keeps its reversed number")
def numbers_kept(ctx):
    data = json.loads((ctx["out"] / "families.json").read_text())
    assert {g["heads"][0]: g["number"] for g in data["groups"][1:]} == ctx["expected"]


@then("a class with two broader classes is refused")
def two_broader():
    script = ("from pdc import families\n"
              "families.build([{'pdc': '1', 'uri': 'u', 'name': 'n', 'broader': ['a', 'b']}])\n")
    out = subprocess.run([sys.executable, "-c", script], cwd=ROOT, capture_output=True, text=True,
                         check=False)
    assert out.returncode != 0 and "2 broader classes" in out.stderr, out.stderr


# --- publishing, with a throwaway key --------------------------------------


@pytest.fixture
def publishing(tmp_path) -> dict:
    """A `pub` that knows families, from PUB_BIN_DIR, and a throwaway key."""
    bin_dir = os.environ.get("PUB_BIN_DIR")
    if not bin_dir:
        pytest.skip("PUB_BIN_DIR names no directory holding a pub that knows families")
    env = dict(os.environ, PATH=f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    home = tmp_path / "key"
    home.mkdir()
    for args in (["init"], ["sign", "--generate-key", "--principal=human", "--label=throwaway"]):
        subprocess.run(["pub", *args], cwd=home, env=env, check=True, capture_output=True)
    return {"env": env, "key": home / ".publet", "corpus": tmp_path / "new"}


def _held(publishing) -> str:
    return subprocess.run(["pub-store", f"--store={publishing['key'] / 'objects.redb'}", "list"],
                          env=publishing["env"], capture_output=True, text=True, check=True).stdout


@given("a throwaway key and a pub that knows families")
def throwaway(publishing):
    publishing["held"] = _held(publishing)


def _publish(publishing):
    return subprocess.run(
        [sys.executable, str(ROOT / "tools" / "publish.py"), f"--key={publishing['key']}",
         f"--corpus={publishing['corpus']}", "--release=0.2.0", "--created=2026-11-02T18:00:00Z"],
        env=publishing["env"], capture_output=True, text=True, check=False)


@when("I publish to a new corpus", target_fixture="result")
def publish_new(publishing):
    return _publish(publishing)


@when("I publish to a corpus that exists", target_fixture="result")
def publish_existing(publishing):
    publishing["corpus"].mkdir()
    return _publish(publishing)


@then("the corpus's edition lists every family by its CID")
def edition_lists(publishing):
    env, corpus = publishing["env"], publishing["corpus"]
    cids = json.loads((corpus / "pdc-cids.json").read_text())
    subprocess.run(["pub", "bundle", "--dir=objects", "--out=bundles"], cwd=corpus, env=env,
                   check=True, capture_output=True)
    edition = json.loads((corpus / "bundles" / "o" / f"{cids['edition']}.json").read_text())
    defines = edition["object"]["body"]["defines"]
    listed = {defines["top"], *(c for s in defines["sections"].values() for c in s.values())}
    assert listed == set(cids["classes"].values()) and len(listed) == 573


@then("the corpus's signing link is gone and the key's store is unchanged")
def nothing_left(publishing):
    assert not (publishing["corpus"] / ".publet" / "signing.key").exists()
    assert _held(publishing) == publishing["held"]
