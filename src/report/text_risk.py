"""The organisation's own score on the page, led by whether the source changes the band.

A finding is scored once per source, so most carry a range; the ones whose band depends on the
source come first. A provisional score (from an Unknown answer) is marked on its own line. The
weighting heads the block; a severity floor and any council vector go on lines under the finding.
"""

from itertools import chain

from organisation.risk import FindingRisk
from report.council_beside import NOT_IN_THE_SCORE, CouncilFigure, council_figure, figure_label
from report.record import Report
from report.risk_order import bands_contested_first
from report.risk_words import FLOORED_BY, PROVISIONAL
from report.text_layout import INDENT, SOURCE_SEPARATOR, section
from scoring.risk_score import RiskScore

WEIGHTING_LABEL = "weighted"
COLUMN_GAP = "  "


def risk_block(report: Report) -> str:
    """Score every finding this environment was asked about, the contested bands first."""
    if not report.risk:
        return ""
    weighed = bands_contested_first(report.risk.values())
    width = id_width(report)
    entries = [risk_entry(one, width, council_figure(report, one.advisory_id)) for one in weighed]
    titled = f"ORGANISATION RISK ({len(weighed)}){headline(report)}"
    return section(titled, [weighting(weighed[0]), *entries])


def weighting(weighed: FindingRisk) -> str:
    """Give the weighting that combined the categories, so the total re-derives on the page."""
    # The weighting is the same on every score and finding, so it is said once.
    named = ", ".join(f"{one.category} {one.weight:g}" for one in weighed.scores[0].weights)
    return f"{INDENT}{WEIGHTING_LABEL} {named}"


def headline(report: Report) -> str:
    """Say how many findings the choice of source would change the response to."""
    contested = [one for one in report.risk.values() if one.band_depends_on_the_source]
    if not contested:
        return ""
    return f"{SOURCE_SEPARATOR}the source changes the band on {len(contested)}"


def risk_entry(weighed: FindingRisk, width: int, figure: CouncilFigure | None) -> str:
    """Give one finding's score or range, its bands, its flag, and any council figure beside it."""
    flag = f"{SOURCE_SEPARATOR}{PROVISIONAL}" if weighed.is_provisional else ""
    bands = " and ".join(weighed.bands)
    scored = f"{INDENT}{weighed.advisory_id.ljust(width)}{COLUMN_GAP}{spread(weighed):<28}{bands}"
    return f"{scored}{flag}{floors_beside(weighed, width)}{beside(figure, width)}"


def floors_beside(weighed: FindingRisk, width: int) -> str:
    """Put each floor that raised a band under the score, naming its rule and both bands."""
    said = chain.from_iterable(floor_lines(one) for one in weighed.scores)
    return "".join(f"\n{score_margin(width)}{line}" for line in said)


def floor_lines(scored: RiskScore) -> list[str]:
    """Name each floor that raised one source's band, from the band before to the band after."""
    named = getattr(scored.technical, "source", "")
    source = f"{named} " if named else ""
    return [
        f"{FLOORED_BY} {floor.rule_id}: {source}{floor.band_before} to {floor.band_after}"
        for floor in scored.floors
    ]


def beside(figure: CouncilFigure | None, width: int) -> str:
    """Put a council's figure under the score it sits beside, saying the score does not use it."""
    if figure is None:
        return ""
    # On its own line so it does not push the bands out of line.
    return f"\n{score_margin(width)}{figure_label(figure)}{SOURCE_SEPARATOR}{NOT_IN_THE_SCORE}"


def score_margin(width: int) -> str:
    """Give the indent that puts a line under the score column of a risk entry."""
    return " " * (len(INDENT) + width + len(COLUMN_GAP))


def spread(weighed: FindingRisk) -> str:
    """Give the one score, or the range with the source at each end of it named."""
    # Attributed only on a range: on a single score there is nothing to attribute between.
    ends = sorted(weighed.scores, key=lambda one: one.score)
    if ends[0].score == ends[-1].score:
        return f"{ends[0].score:.1f}"
    return f"{labelled(ends[0])} to {labelled(ends[-1])}"


def labelled(scored: RiskScore) -> str:
    """Name one end of a range by the source that put it there."""
    named = getattr(scored.technical, "source", "")
    return f"{named} {scored.score:.1f}" if named else f"{scored.score:.1f}"


def id_width(report: Report) -> int:
    """Widen the id column to the longest advisory id scored, rather than guessing one."""
    return max(len(advisory_id) for advisory_id in report.risk)
