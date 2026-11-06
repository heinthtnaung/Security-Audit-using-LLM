"""The typography the terminal rendering shares: spacing, columns, re-flowing, a titled block.

Column widths are measured off the content, so a long identifier does not push a row out of line.
"""

from textwrap import fill

INDENT = "  "
SOURCE_SEPARATOR = "  ·  "
NAME_WIDTH = 30
# What a re-flowed line wraps at, margin included.
PAGE_WIDTH = 96


def section(title: str, entries: list[str]) -> str:
    """Put a titled block together."""
    return "\n".join([title, *entries])


def named(finding) -> str:
    """Name the component a finding is against, padded so the columns line up."""
    return f"{finding.component.name} {finding.component.version}".ljust(NAME_WIDTH)


def identified(finding, width: int) -> str:
    """Give the advisory id, padded to the widest in its own group."""
    return finding.advisory.advisory_id.ljust(width)


def id_width(findings: tuple) -> int:
    """Widen the id column to the longest id present rather than guessing one."""
    return max((len(one.advisory.advisory_id) for one in findings), default=0)


def indented(depth: int, said: str) -> str:
    """Put one line at its depth on the page."""
    return f"{INDENT * depth}{said}"


def wrapped(said: str, depth: int) -> list[str]:
    """Re-flow one long line to the width of the page at its depth, losing no word of it."""
    margin = INDENT * depth
    # Broken at spaces only: hyphenating would invent words, so a long word runs past the edge.
    flowed = fill(
        said, width=PAGE_WIDTH, initial_indent=margin, subsequent_indent=margin,
        break_on_hyphens=False, break_long_words=False,
    )
    return flowed.split("\n")
