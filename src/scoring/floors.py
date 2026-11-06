"""The severity floors: a band an answer can raise, whatever the weighted total came to.

Some facts should not be averaged away, so these rules set a band the score may
not fall below. Only the band moves, never the number, and every floor that raised
it is recorded. Only an explicit Yes triggers one, and a floor never lowers a band.
"""

from dataclasses import dataclass
from typing import Mapping

from scoring.bands import RISK_BANDS
from scoring.library import question
from scoring.question import Answer

# Lowest first, so a higher rank is a more severe band.
BAND_RANK: Mapping[str, int] = {name: rank for rank, (_, name) in enumerate(reversed(RISK_BANDS))}


@dataclass(frozen=True)
class SeverityFloor:
    """One rule: the questions an explicit Yes to all of must meet, the band it sets, and why."""

    rule_id: str
    answered_yes: tuple[str, ...]
    floor_band: str
    reason: str

    def __post_init__(self) -> None:
        """Refuse a rule that names a question nobody approved or a band the scale lacks."""
        if not self.rule_id or not self.answered_yes or not self.reason:
            raise ValueError("A severity floor needs an id, the answers it reads, and its reason")
        for identifier in self.answered_yes:
            question(identifier)
        if self.floor_band not in BAND_RANK:
            raise ValueError(f"{self.rule_id}: {self.floor_band!r} is no organisation band")


@dataclass(frozen=True)
class AppliedFloor:
    """One floor that raised a band: which rule, the answers that met it, and both bands."""

    rule_id: str
    answered_yes: tuple[str, ...]
    band_before: str
    band_after: str


# Ascending by the band each sets, so the first can raise a band the second raises again.
SEVERITY_FLOORS: tuple[SeverityFloor, ...] = (
    SeverityFloor(
        "FLOOR-EXPLOITED-HIGH",
        ("THR-1",),
        "High",
        "a vulnerability exploited in the wild is being used against somebody now, "
        "and no weighting of this environment should put it below High",
    ),
    SeverityFloor(
        "FLOOR-EXPLOITED-EXPOSED-CRITICAL",
        ("THR-1", "EXP-1", "BUS-1"),
        "Critical",
        "exploited in the wild, on an internet-facing service, on a business-critical "
        "asset is the case this score exists to catch, and it is Critical",
    ),
)


def applied_floors(band: str, answers: Mapping[str, Answer]) -> tuple[AppliedFloor, ...]:
    """Raise a band by every floor its answers meet, in order, recording each that raised it."""
    applied = []
    for rule in SEVERITY_FLOORS:
        if not meets(rule, answers) or BAND_RANK[rule.floor_band] <= BAND_RANK[band]:
            continue
        applied.append(AppliedFloor(rule.rule_id, rule.answered_yes, band, rule.floor_band))
        band = rule.floor_band
    return tuple(applied)


def meets(rule: SeverityFloor, answers: Mapping[str, Answer]) -> bool:
    """Say whether every question the rule reads was answered an explicit Yes."""
    # An unanswered question, like Unknown and N/A, is not a Yes.
    return all(answers.get(identifier) is Answer.YES for identifier in rule.answered_yes)


def floored_band(score_band: str, floors: tuple[AppliedFloor, ...]) -> str:
    """Give the band after its floors: the last one raised it, or none did and it stands."""
    return floors[-1].band_after if floors else score_band
