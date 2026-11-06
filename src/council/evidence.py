"""The quotation check: is a member's evidence really in the text it was shown?

Checked against the redacted text the member read, not the raw advisory.
"Appears in" means an exact substring after folding whitespace runs to one space
and typographic quotes to ASCII; case is not folded and no words are dropped, so
a paraphrase cannot pass. A quotation of only a redaction marker does not count:
it must carry a word of the advisory's own outside any marker.
"""

import re

from council.redaction import REDACTIONS

# Quote characters a model substitutes without changing what was said.
TYPOGRAPHIC_EQUIVALENTS = {
    "‘": "'",
    "’": "'",
    "‚": "'",
    "“": '"',
    "”": '"',
    "„": '"',
    "′": "'",
    "″": '"',
}

WHITESPACE_RUN = re.compile(r"\s+")

# A member never sees a CVE id; text that still carries one was never redacted.
CVE_IDENTIFIER = re.compile(r"CVE-\d{4}-\d{4,}", re.IGNORECASE)

# A quotation must contain a word; punctuation alone would verify anywhere.
WORD_CHARACTER = re.compile(r"\w")

# The markers this system inserts, read off `REDACTIONS` so the two cannot drift.
REDACTION_MARKERS: tuple[str, ...] = tuple(dict.fromkeys(m for _, m in REDACTIONS))


def is_quotation_from(quotation: str, advisory_text: str) -> bool:
    """Say whether a member's evidence is really present in the advisory it read."""
    refuse_empty_advisory(advisory_text)
    refuse_unredacted(advisory_text)
    if not quotes_the_advisory(quotation):
        return False
    return normalise(quotation) in normalise(advisory_text)


def quotes_the_advisory(quotation: str) -> bool:
    """Say whether a quotation carries a word of the advisory's own, outside any marker."""
    return bool(WORD_CHARACTER.search(without_markers(quotation)))


def without_markers(text: str) -> str:
    """Take out what this system substituted, leaving only what the advisory said."""
    for marker in REDACTION_MARKERS:
        text = text.replace(marker, " ")
    return text


def normalise(text: str) -> str:
    """Fold the layout and the typography, and nothing that changes a word."""
    folded = "".join(TYPOGRAPHIC_EQUIVALENTS.get(character, character) for character in text)
    return WHITESPACE_RUN.sub(" ", folded).strip()


def refuse_unredacted(advisory_text: str) -> None:
    """Refuse advisory text still carrying a CVE id, which is not what a member read."""
    found = CVE_IDENTIFIER.search(advisory_text)
    if not found:
        return
    raise ValueError(
        f"This advisory text still contains {found.group()}, so it is not the text a "
        "member was shown: the panel rule keeps the CVE id away from a member. Check a "
        "quotation against the redacted text the member read, not the raw advisory."
    )


def refuse_empty_advisory(advisory_text: str) -> None:
    """Refuse to check against text that is not there, rather than failing every member."""
    # Returning False here would read as every member failing; empty text is a broken finding.
    if not isinstance(advisory_text, str):
        raise TypeError(f"An advisory must be text, not {type(advisory_text).__name__}")
    if not advisory_text.strip():
        raise ValueError("There is no advisory text to check a quotation against")
