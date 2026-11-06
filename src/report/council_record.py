"""What a council did, projected into types the report can hold without importing the council.

One record per member, with its kind named on every row. The arithmetic has already
happened in `council`, so what is left here is a row to write down.
"""

from dataclasses import dataclass
from enum import Enum


class SaidKind(Enum):
    """What a member did about one metric."""

    ANSWERED = "answered"
    DECLINED = "declined"
    GUESSED = "guessed"
    FAILED = "failed"
    # Gave one value with the options in order, another reversed: the list decided it.
    ORDER_SENSITIVE = "order-sensitive"


class ReadingOrder(Enum):
    """Which order a member read a metric's options in, asked them both ways."""

    IN_ORDER = "in_order"
    REVERSED = "reversed"


class Outcome(Enum):
    """What the chairman made of one metric."""

    SETTLED = "settled"
    CONTESTED = "contested"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class MemberIdentity:
    """Which member spoke, and enough to reconstruct the roster."""

    name: str
    provider: str
    model: str
    family: str
    ran_local: bool
    prompt_version: str
    # Empty unless the member was also asked the options reversed.
    reversed_prompt_version: str = ""


@dataclass(frozen=True)
class MemberSaid:
    """What one member said about one metric, and who said it.

    `value`, `evidence` and `confidence` are empty for the kinds that have none; `kind` says
    which. `order_values` holds an order-sensitive member's two values. `declined_in` and
    `unverified_in` name the orders it declined or failed verification in, empty if asked once.
    """

    member: MemberIdentity
    kind: SaidKind
    value: str = ""
    evidence: str = ""
    confidence: str = ""
    verified: bool = False
    reason: str = ""
    order_values: tuple[str, ...] = ()
    declined_in: tuple[ReadingOrder, ...] = ()
    unverified_in: tuple[ReadingOrder, ...] = ()


@dataclass(frozen=True)
class MetricEscalation:
    """A metric the council left open, put to the escalation model, and what that model said.

    `prior` is what the council left it as; the ruling holding this says what came of it.
    """

    prior: Outcome
    said: MemberSaid


@dataclass(frozen=True)
class MetricRuling:
    """What the chairman decided about one metric, and what every member said first.

    `escalation` is None where the council settled the metric, or no escalation model was named.
    `same_evidence_different_reading` flags members whose verified quotations match but whose
    values differ; it is shown beside the ruling and decides nothing.
    """

    metric: str
    outcome: Outcome
    said: tuple[MemberSaid, ...]
    value: str = ""
    basis: str = ""
    confidence: str = ""
    fallback_source: str = ""
    escalation: MetricEscalation | None = None
    same_evidence_different_reading: bool = False


@dataclass(frozen=True)
class CouncilAssessment:
    """A council that settled every metric for one advisory, and the vector it handed over."""

    advisory_id: str
    vector: str
    single_assessor: bool
    rulings: tuple[MetricRuling, ...] = ()
    # No metric on the vector was cross-checked: one member reached, or every
    # metric rests on a single member's quotation. Set in `cli.council_run`.
    nothing_cross_checked: bool = False


@dataclass(frozen=True)
class CouncilNotAsked:
    """A finding no council was put to, and why -- not the same as no council having run.

    Tell apart: not asked (this), assessed but unsettled (`CouncilWithoutVector`), and no
    council at all (no entry). `because` is set where the skip is, not here.
    """

    advisory_id: str
    because: str

    def __post_init__(self) -> None:
        """Refuse a skip that does not say why."""
        if not self.because:
            raise ValueError(
                f"{self.advisory_id} was not put to the council and no reason was recorded"
            )


@dataclass(frozen=True)
class CouncilWithoutVector:
    """A council that ran on one advisory and could not settle a vector, and what stopped it.

    Its own type: a council that ran and settled nothing is a result, not an absence.
    """

    advisory_id: str
    single_assessor: bool
    unresolved_metrics: tuple[str, ...] = ()
    contested_metrics: tuple[str, ...] = ()
    rulings: tuple[MetricRuling, ...] = ()


CouncilOutcome = CouncilAssessment | CouncilWithoutVector | CouncilNotAsked
