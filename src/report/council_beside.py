"""A vector a council settled, shown beside the Organisation Risk Score and never used in it.

Its figure is the vector's own CVSS base score, not an organisation score. The figure and
its wording live here so no rendering recomputes either.
"""

from dataclasses import dataclass

from cvss.score import base_score, severity_band
from cvss.vector import parse
from report.council_record import CouncilAssessment
from report.record import Report

COUNCIL_SOURCE = "the assessor council"
NOT_IN_THE_SCORE = "the risk score does not use it"
CVSS_SCALE_NAME = "CVSS"


@dataclass(frozen=True)
class CouncilFigure:
    """The vector a council settled for one finding, and the CVSS base score it computes to."""

    vector: str
    base_score: float

    @property
    def band(self) -> str:
        """Name the CVSS severity band the base score lands in."""
        return severity_band(self.base_score)


def figure_of(settled: CouncilAssessment) -> CouncilFigure:
    """Give the vector one council settled, and the CVSS base score it computes to."""
    return CouncilFigure(settled.vector, base_score(parse(settled.vector)))


def council_figure(report: Report, advisory_id: str) -> CouncilFigure | None:
    """Give the vector a council settled for one finding, or None where it settled none."""
    settled = report.council.get(advisory_id)
    if not isinstance(settled, CouncilAssessment):
        return None
    return figure_of(settled)


def on_its_scale(figure: CouncilFigure) -> str:
    """Give the base score with the scale it is on."""
    return f"{CVSS_SCALE_NAME} {figure.base_score:.1f}"


def figure_label(figure: CouncilFigure) -> str:
    """Name the council's figure with its source and scale."""
    return f"{COUNCIL_SOURCE} {on_its_scale(figure)}"


def banded(figure: CouncilFigure) -> str:
    """Give the figure on its scale with its CVSS band."""
    return f"{on_its_scale(figure)} {figure.band}"
