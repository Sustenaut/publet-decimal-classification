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


@then(parsers.parse('the imported class "{code}" is a concept named "{name}"'))
def concept_named(code: str, name: str):
    defines = _imported(code)["claim"]["defines"]
    assert defines["sort"] == "concept" and defines["pdc"] == code, defines
    assert defines["name"] == name, defines
    assert "kind" not in defines and "relation" not in defines, defines


@then(parsers.parse('the imported class "{code}" matches "{prefix}"'))
def concept_matches(code: str, prefix: str):
    matches = _imported(code)["claim"]["defines"]["matches"]
    assert matches[0]["ref"].startswith(prefix), matches


@then(parsers.parse('the imported class "{code}" is under "{parent}"'))
def concept_under(code: str, parent: str):
    assert parent in _imported(code)["broader"]


STEWARD = "pub:sha2-256:ue7bjgletvpfendw4dptudm64oaaqaoia3pu7vnao6xq6fq5o6jq"


def _object(cid: str) -> Path:
    return ROOT / "corpus" / "objects" / f"{cid.replace(':', '_')}.cbor"


@then("every imported class has a concept object in corpus/objects/ under its CID in data/pdc/cids.json")
def every_class_signed():
    data = json.loads((ROOT / "data" / "pdc" / "udc-summary.json").read_text())
    cids = json.loads((ROOT / "data" / "pdc" / "cids.json").read_text())
    assert set(cids) == {c["pdc"] for c in data["classes"]}
    for code, cid in cids.items():
        body = _object(cid).read_bytes()
        assert hashlib.sha256(body).digest() == _digest(cid), code
        assert code.encode() in body, code


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
