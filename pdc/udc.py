"""Reading the UDC Summary's SKOS data."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rdflib import RDF, Graph, Namespace, URIRef

SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")


@dataclass(frozen=True)
class UdcClass:
    """One class: its notation, URI, English label and scope notes, and the
    URIs of its broader classes."""

    uri: str
    notation: str
    label: str | None
    scope_notes: tuple[str, ...]
    broader: tuple[str, ...]


def _english(graph: Graph, subject: URIRef, predicate: URIRef) -> list[str]:
    return sorted(
        " ".join(str(o).split())
        for o in graph.objects(subject, predicate)
        if getattr(o, "language", None) == "en" and str(o).strip()
    )


def load(path: Path) -> list[UdcClass]:
    """Every `skos:Concept` in the file, sorted by URI."""
    graph = Graph()
    graph.parse(path, format="turtle")
    out = []
    for subject in sorted(graph.subjects(RDF.type, SKOS.Concept)):
        notations = [str(n) for n in graph.objects(subject, SKOS.notation)]
        if len(notations) != 1:
            raise ValueError(f"{subject} has {len(notations)} notations, not one")
        labels = _english(graph, subject, SKOS.prefLabel)
        out.append(UdcClass(
            uri=str(subject),
            notation=notations[0],
            label=labels[0] if labels else None,
            scope_notes=tuple(_english(graph, subject, SKOS.scopeNote)),
            broader=tuple(sorted(str(b) for b in graph.objects(subject, SKOS.broader))),
        ))
    return out
