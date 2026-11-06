"""Take out of an advisory the things a member must not see.

A member reads the advisory text only, never the CVE id or the published scores:
a model that recognises an id recites it from training. CVE and GHSA ids and CVSS
vectors (with or without the `CVSS:3.1/` prefix) are replaced by a marker, so a
sentence still reads as one. Two gaps stay open and are tested: a score written in
prose, and identifier namespaces other than CVE and GHSA. The redacted text is
what `council.evidence` checks quotations against, never the original.
"""

import re
from dataclasses import dataclass

# Non-capturing, so `findall` returns whole matches. Identifier length is
# unbounded: a CVE sequence number has no upper limit, and guessing one would let
# through the ids this exists to stop. `council.evidence` uses a matching pattern.
CVE_IDENTIFIER = re.compile(r"\bCVE-\d{4}-\d{4,}\b", re.IGNORECASE)
GHSA_IDENTIFIER = re.compile(r"\bGHSA(?:-[0-9a-z]{4,})+\b", re.IGNORECASE)

# One metric of a vector, as loose in the key as CVSS is (v2, v3.1 and v4.0 keys).
METRIC_PAIR = r"[A-Za-z]+:[A-Za-z]"

# The metrics a vector opens with, across v2, v3.1 and v4.0. A bare vector must
# start at one of these, which keeps the pattern off a URL's `host:p/` or a
# `16:9/4:3` ratio. Single-letter keys (S, C, I, A) are not openings: one letter
# cannot be told from a coincidence.
VECTOR_OPENING = "AV|AC|Au|AT|PR|UI|VC|VI|VA|SC|SI|SA"

PUBLISHED_VECTOR = re.compile(rf"\bCVSS:\d\.\d(?:/{METRIC_PAIR})+")
BARE_VECTOR = re.compile(rf"\b(?:{VECTOR_OPENING}):[A-Za-z](?:/{METRIC_PAIR})+")

IDENTIFIER_MARKER = "[identifier withheld]"
VECTOR_MARKER = "[published score withheld]"

# The prefixed vector goes first, so it takes the `CVSS:3.1/` with it rather than
# leaving it in front of a marker.
REDACTIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (PUBLISHED_VECTOR, VECTOR_MARKER),
    (BARE_VECTOR, VECTOR_MARKER),
    (CVE_IDENTIFIER, IDENTIFIER_MARKER),
    (GHSA_IDENTIFIER, IDENTIFIER_MARKER),
)


@dataclass(frozen=True)
class RedactedAdvisory:
    """An advisory as a member will see it, and every string taken out of it.

    `removed` is a log, not a set: in `REDACTIONS` order, with a repeat listed
    each time, so its length counts redactions and not distinct secrets.
    """

    text: str
    removed: tuple[str, ...]


def redact(advisory_text: str) -> RedactedAdvisory:
    """Take the identifiers and published vectors out of an advisory, keeping a record."""
    refuse_empty(advisory_text)
    removed: list[str] = []
    text = advisory_text
    for pattern, marker in REDACTIONS:
        text, found = replace_all(text, pattern, marker)
        removed.extend(found)
    return RedactedAdvisory(text=text, removed=tuple(removed))


def replace_all(text: str, pattern: re.Pattern[str], marker: str) -> tuple[str, list[str]]:
    """Replace every match with a marker, and say what was replaced."""
    return pattern.sub(marker, text), pattern.findall(text)


def refuse_empty(advisory_text: str) -> None:
    """Refuse an advisory with no text, rather than prompting a member with nothing."""
    if not isinstance(advisory_text, str):
        raise TypeError(f"An advisory must be text, not {type(advisory_text).__name__}")
    if not advisory_text.strip():
        raise ValueError("There is no advisory text to assess")
