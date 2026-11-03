"""Grouping the imported classes into families (publet spec Section 5.9.1).

A family defines the classes directly under one class, in one claim. Every
class is in exactly one family, and the top family holds the two UDC roots.
Each family names the one auxiliary grouping its classes may use.

A special auxiliary is told by its notation, as UDC writes one: a hyphen
between digits (`62-1`), a backtick before a digit (`81`1`), or `.0` and a
digit (`7.01`). Its **head** is the highest class written so, which the family
of the class it refines lists under `auxiliaries`. Everything beneath a head
is an ordinary family in the special-auxiliaries section.

A **group** is a numbered list of table heads: the six common tables under
`---` are group 1, and each special auxiliary head is a group of its own. A
**grouping** is a numbered set of groups: the common tables, and the special
auxiliaries of a family's parent and every class above it, so that under `616`
those of `61` and of `616` both apply.

Groups and groupings only grow, and a number never changes its meaning, so
each import keeps what the previous one numbered and adds new numbers after it.
"""

from __future__ import annotations

import re
from collections import defaultdict

AUXILIARY_ROOT = "-"
COMMON_TABLES = "---"
SECTIONS = ("main", "common-auxiliaries", "special-auxiliaries")

_SPECIAL = re.compile(r"\d-\d|`\d|\.0\d")


def is_special(notation: str) -> bool:
    """Whether a notation is written as a special auxiliary is."""
    return bool(_SPECIAL.search(notation))


def _member(entry: dict, parents: set[str]) -> dict:
    member = {"pdc": entry["pdc"], "name": entry["name"]}
    if entry.get("boundary"):
        member["boundary"] = entry["boundary"]
    member["matches"] = [{"relation": "exact", "ref": entry["uri"]}]
    if entry["pdc"] in parents:
        member["children"] = True
    return member


def _content(parent: str | None, names: dict[str, str]) -> str:
    if parent is None:
        return "The PDC classes with no broader class."
    return f"The PDC classes directly under {parent} {names[parent].rstrip(chr(46))}."


def _number(previous: list[dict], key: str) -> dict[frozenset, int]:
    return {frozenset(entry[key]): entry["number"] for entry in previous}


def build(entries: list[dict], previous: dict | None = None) -> dict:
    """The families of `entries`, each with one parent code or none, keeping
    the group and grouping numbers of `previous`, an earlier result."""
    previous = previous or {"groups": [], "groupings": []}
    names = {e["pdc"]: e["name"] for e in entries}
    children: dict[str | None, list[dict]] = defaultdict(list)
    parent_of: dict[str, str | None] = {}
    for entry in entries:
        broader = entry["broader"]
        if len(broader) > 1:
            raise ValueError(f"{entry['pdc']} has {len(broader)} broader classes, not one")
        parent = broader[0] if broader else None
        parent_of[entry["pdc"]] = parent
        children[parent].append(entry)
    parents = {p for p in children if p is not None}

    def above(code: str | None) -> list[str]:
        out = []
        while code is not None:
            out.append(code)
            code = parent_of[code]
        return out

    heads = {e["pdc"] for e in entries
             if is_special(e["pdc"]) and not is_special(parent_of[e["pdc"]] or "")}
    common = sorted(e["pdc"] for e in children[COMMON_TABLES])
    groups = [dict(g, heads=list(g["heads"])) for g in previous["groups"]]
    if groups:
        first = groups[0]
        first["heads"] = sorted(set(first["heads"]) | set(common))
    else:
        groups.append({"number": 1, "heads": common})
    numbered = {head: g["number"] for g in groups[1:] for head in g["heads"]}
    for head in sorted(heads - set(numbered)):
        number = max(g["number"] for g in groups) + 1
        groups.append({"number": number, "heads": [head]})
        numbered[head] = number

    groupings = [dict(g, groups=list(g["groups"])) for g in previous["groupings"]]
    known = _number(groupings, "groups")

    def grouping_of(parent: str | None) -> int:
        applying = {1}
        applying.update(numbered[e["pdc"]] for code in above(parent)
                        for e in children[code] if e["pdc"] in heads)
        key = frozenset(applying)
        if key not in known:
            known[key] = max([g["number"] for g in groupings], default=0) + 1
            groupings.append({"number": known[key], "groups": sorted(applying)})
        return known[key]

    families = []
    counts = {name: {"families": 0, "classes": 0, "auxiliaries": 0} for name in (*SECTIONS, "total")}
    for parent in sorted(children, key=lambda p: (p is not None, p or "")):
        under = children[parent]
        members = [_member(e, parents) for e in under if e["pdc"] not in heads]
        auxiliaries = [_member(e, parents) for e in under if e["pdc"] in heads]
        chain = above(parent)
        if parent is None:
            section = None
        elif any(is_special(code) for code in chain):
            section = "special-auxiliaries"
        elif AUXILIARY_ROOT in chain:
            section = "common-auxiliaries"
        else:
            section = "main"
        defines = {"sort": "family"}
        if parent is not None:
            defines["parent"] = parent
        defines["grouping"] = grouping_of(parent)
        defines["members"] = members
        if auxiliaries:
            defines["auxiliaries"] = auxiliaries
        families.append({"section": section, "content": _content(parent, names), "defines": defines})
        for name in (section, "total"):
            if name:
                counts[name]["families"] += 1
                counts[name]["classes"] += len(members)
                counts[name]["auxiliaries"] += len(auxiliaries)
    counts["groups"] = len(groups)
    counts["groupings"] = len(groupings)
    return {"groups": groups, "groupings": sorted(groupings, key=lambda g: g["number"]),
            "counts": counts, "families": families}


def edition(result: dict, cids: dict[str | None, str]) -> dict:
    """An edition's `defines`, given each family's CID by parent code."""
    sections: dict[str, dict[str, str]] = {name: {} for name in SECTIONS}
    top = None
    for family in result["families"]:
        parent = family["defines"].get("parent")
        if parent is None:
            top = cids[None]
        else:
            sections[family["section"]][parent] = cids[parent]
    return {"sort": "edition", "top": top, "sections": sections, "groups": result["groups"],
            "groupings": result["groupings"], "counts": result["counts"]}
