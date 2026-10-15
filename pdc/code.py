"""PDC codes: a UDC Summary notation, or one extended by a PDC number.

A PDC class narrower than a UDC class is written

    <UDC notation> ~ <PDC number>          e.g. 631.544~1, 631.544~12

`~` is the separator because UDC notation never uses it: not in the UDC
Summary (the importer checks every notation in the pinned file, and
refuses one that does), and not among the signs of UDC syntax, which are
`+ / : :: [ ] = ( ) " - . ' * A/Z` and digits. It is also an unreserved
character in URLs (RFC 3986) and valid in file names, so a code is usable
as is in `https://pub.<host>/def/<code>` and as a path.

The PDC number is decimal, as UDC's are: one digit per level, so the
broader class of `631.544~12` is `631.544~1`, and that of `631.544~1` is
the UDC class `631.544`. A level holds ten narrower classes, `0` to `9`.
Points, which UDC inserts every three digits for reading, are not used.
"""

from __future__ import annotations

import re

SEPARATOR = "~"
_NUMBER = re.compile(r"[0-9]+")


def is_extension(code: str) -> bool:
    """Whether `code` is a PDC class rather than a UDC Summary class."""
    return SEPARATOR in code


def problems(code: str, udc: set[str]) -> list[str]:
    """Why `code` is not a valid PDC code, given the UDC Summary notations.

    Empty when it is valid: a notation in `udc`, or such a notation, the
    separator, and a PDC number of one or more digits.
    """
    if not is_extension(code):
        return [] if code in udc else [f"{code!r} is not a UDC Summary notation"]
    base, _, number = code.partition(SEPARATOR)
    out = []
    if base not in udc:
        out.append(f"{base!r}, before {SEPARATOR!r}, is not a UDC Summary notation")
    if not _NUMBER.fullmatch(number):
        out.append(f"{number!r}, after {SEPARATOR!r}, is not a PDC number: digits only")
    return out


def broader(code: str) -> str | None:
    """The code of the class a PDC class is narrower than, read from the code.

    `None` for a UDC Summary class: its broader class is UDC's own
    `skos:broader`, which the notation does not always show.
    """
    if not is_extension(code):
        return None
    base, _, number = code.partition(SEPARATOR)
    return base if len(number) == 1 else f"{base}{SEPARATOR}{number[:-1]}"
