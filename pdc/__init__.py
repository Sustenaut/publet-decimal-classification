"""The Extended Publet Decimal Classification (PDC).

The UDC Summary's classes under their own codes, extended by narrower PDC
classes whose codes extend a UDC code (publet spec Section 5.9.1).
"""

from __future__ import annotations

import json
from pathlib import Path

_HERE = Path(__file__).resolve().parent
# pip installs data/pdc/ as the package pdc.data (pyproject.toml).
_INSTALLED = _HERE / "data"
_CHECKOUT = _HERE.parent / "data" / "pdc"


def data_dir() -> Path:
    """Where the generated PDC data is: in the installed package, or data/pdc/ in a checkout."""
    return _INSTALLED if (_INSTALLED / "udc-summary.json").is_file() else _CHECKOUT


def classes() -> list[dict]:
    """Every imported class: its code (`pdc`), UDC URI, broader classes and concept claim."""
    return json.loads((data_dir() / "udc-summary.json").read_text())["classes"]


def cids() -> dict[str, str]:
    """Each code's signed concept claim, by CID."""
    return json.loads((data_dir() / "cids.json").read_text())
