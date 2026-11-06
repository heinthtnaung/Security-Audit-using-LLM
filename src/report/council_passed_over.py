"""The findings a council was not put to, grouped by reason, once for every rendering.

Each skip keeps its reason (`CouncilNotAsked`); the renderings list them by reason and id.
"""

from dataclasses import dataclass
from typing import Sequence

from report.council_record import CouncilNotAsked


@dataclass(frozen=True)
class PassedOver:
    """One reason the council was not put to some findings, and which findings they were."""

    because: str
    advisory_ids: tuple[str, ...]


def grouped_by_reason(passed: Sequence[CouncilNotAsked]) -> tuple[PassedOver, ...]:
    """Group the findings the council was not put to by the reason it was not put to them."""
    reasons = sorted({one.because for one in passed})
    return tuple(PassedOver(one, named_for(one, passed)) for one in reasons)


def named_for(because: str, passed: Sequence[CouncilNotAsked]) -> tuple[str, ...]:
    """Name every finding passed over for one reason, in the order the record holds them."""
    return tuple(one.advisory_id for one in passed if one.because == because)
