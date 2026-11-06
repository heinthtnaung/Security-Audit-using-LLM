"""The reply types a member can return about one metric, and who returned it.

An answer carries a quotation; a no-evidence and a guess carry none. The two are
kept apart because an absence is a fact about the advisory and a guess about the
member. Nothing here calls a model.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from cvss.metrics import METRIC_ORDER, refuse_illegal_pair


class Confidence(Enum):
    """How sure a member is of the value it supports."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# Weakest first; the chairman reads this order rather than averaging.
CONFIDENCE_ORDER: tuple[Confidence, ...] = (Confidence.LOW, Confidence.MEDIUM, Confidence.HIGH)


@dataclass(frozen=True)
class MemberIdentity:
    """Which member answered, what model it was, and whether the text stayed local.

    `reversed_prompt_version` is set only when the member was asked both orders
    (`council.order_check`), empty otherwise.
    """

    name: str
    provider: str
    model: str
    family: str
    ran_local: bool
    prompt_version: str
    reversed_prompt_version: str = ""

    def __post_init__(self) -> None:
        """Refuse an identity a reader could not reconstruct the run from."""
        missing = [
            field
            for field in ("name", "provider", "model", "family", "prompt_version")
            if not getattr(self, field)
        ]
        if missing:
            raise ValueError(f"A member identity needs {', '.join(missing)}")
        if not isinstance(self.ran_local, bool):
            raise TypeError(
                f"{self.name!r} must say whether it ran local, not {type(self.ran_local).__name__}"
            )


@dataclass(frozen=True)
class MemberAnswer:
    """One member's value for one metric, and the quotation it says supports it."""

    metric: str
    value: str
    evidence: str
    confidence: Confidence
    member: MemberIdentity

    def __post_init__(self) -> None:
        """Refuse an answer naming no real metric, no legal value, or no quotation."""
        refuse_illegal_pair(self.metric, self.value)
        if not self.evidence.strip():
            raise ValueError(f"{self.metric} was answered with no quotation at all")
        if not isinstance(self.confidence, Confidence):
            raise TypeError(
                f"{self.metric} needs a Confidence, not {type(self.confidence).__name__}"
            )
        refuse_unnamed_member(self.metric, self.member)


@dataclass(frozen=True)
class MemberFoundNoEvidence:
    """One member reporting that the advisory says nothing about a metric."""

    metric: str
    member: MemberIdentity

    def __post_init__(self) -> None:
        """Refuse an absence that names no real metric or no member."""
        if self.metric not in METRIC_ORDER:
            raise ValueError(
                f"{self.metric!r} is not a CVSS Base metric; "
                f"the eight are {', '.join(METRIC_ORDER)}"
            )
        refuse_unnamed_member(self.metric, self.member)


@dataclass(frozen=True)
class MemberGuessed:
    """One member offering a value it could not quote the advisory in support of."""

    metric: str
    value: str
    member: MemberIdentity

    def __post_init__(self) -> None:
        """Refuse a guess that is not even a legal reading of the metric."""
        # The value never moves a score; it records which way the member leaned.
        refuse_illegal_pair(self.metric, self.value)
        refuse_unnamed_member(self.metric, self.member)


@dataclass(frozen=True)
class MemberOrderSensitive:
    """One member whose value flipped when the metric's options were reversed.

    The order decided the answer, so like a decline it can neither support nor
    contest a value. Both readings are kept, in-order first.
    """

    metric: str
    in_order_value: str
    reversed_value: str
    member: MemberIdentity

    def __post_init__(self) -> None:
        """Refuse two readings that are not both legal, or not different at all."""
        refuse_illegal_pair(self.metric, self.in_order_value)
        refuse_illegal_pair(self.metric, self.reversed_value)
        if self.in_order_value == self.reversed_value:
            raise ValueError(f"{self.metric} read {self.in_order_value} both ways is stable")
        refuse_unnamed_member(self.metric, self.member)


MemberReply = MemberAnswer | MemberFoundNoEvidence | MemberGuessed | MemberOrderSensitive


def refuse_unnamed_member(metric: str, member: object) -> None:
    """Refuse a reply that does not say which member gave it."""
    if isinstance(member, MemberIdentity):
        return
    raise TypeError(
        f"{metric} must name the member that replied, not {type(member).__name__}"
    )


def weakest_confidence(answers: Iterable[MemberAnswer]) -> Confidence:
    """Give the least certain confidence among several answers, refusing none at all."""
    confidences = [answer.confidence for answer in answers]
    if not confidences:
        raise ValueError("No answers to take a confidence from")
    return min(confidences, key=CONFIDENCE_ORDER.index)
