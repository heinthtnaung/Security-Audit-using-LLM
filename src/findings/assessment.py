"""What one source published about one advisory, read and scored on its own.

Each source is read separately and none is preferred. A source whose vector this
calculator cannot read is kept as unscored, never dropped or scored zero. The two
records are separate types so "nobody scored this" and "scored this 0.0" cannot be
confused.
"""

from dataclasses import dataclass

from cvss.score import base_score
from cvss.vector import CvssVector, parse
from deps.trivy_report import Advisory


@dataclass(frozen=True)
class SourceScore:
    """One source's published vector, quoted, and the base score derived from it."""

    source: str
    # The string as published, never edited.
    vector: str
    # The same reading in this project's terms, kept so disputed metrics need no re-parse.
    parsed_vector: CvssVector
    base_score: float


@dataclass(frozen=True)
class UnreadableSource:
    """One source's published vector that this calculator refused, kept with the reason."""

    source: str
    vector: str
    refusal: str


ReadSource = SourceScore | UnreadableSource


def read_sources(advisory: Advisory) -> list[ReadSource]:
    """Read every source that published a vector for an advisory, in source-name order."""
    # Sorted here, so a hand-made advisory orders its sources like a scanned one.
    return [read_source(source, text) for source, text in sorted(advisory.vectors.items())]


def read_source(source: str, published: str) -> ReadSource:
    """Score one source's published vector, or record why it could not be read."""
    try:
        parsed = parse(published)
    except ValueError as refusal:
        return UnreadableSource(source=source, vector=published, refusal=str(refusal))
    return SourceScore(
        source=source,
        vector=published,
        parsed_vector=parsed,
        base_score=base_score(parsed),
    )
