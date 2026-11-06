"""What one council did over one advisory: every round, who was asked, who was not.

The record lives apart from the dispatch that fills it (`council.runner`). Each
round holds its replies in roster order, whatever order the calls were made in.
"""

from dataclasses import dataclass
from itertools import chain

from council.answer import MemberIdentity, MemberReply
from council.roster import SkippedMember
from council.ruling import MetricRuling


@dataclass(frozen=True)
class MemberFailure:
    """A member that was asked one metric and gave back nothing usable, and why.

    Not a member that was never asked (`CouncilRun.skipped`): this one was reached
    and its call failed, or its reply could not be read.
    """

    member: MemberIdentity
    metric: str
    reason: str


@dataclass(frozen=True)
class OrderReadings:
    """One member's two readings of one metric, options in order and reversed.

    `council.order_check.reconciled` makes the pair one reply. The pair is kept
    because that one reply cannot say which order a member declined in.
    """

    in_order: MemberReply | MemberFailure
    reversed_order: MemberReply | MemberFailure


@dataclass(frozen=True)
class MetricEscalation:
    """A metric the council left open, put to the escalation model in both orders.

    `prior` is the ruling the council reached; `reply` is the escalation model's
    two `readings` made one. The outcome is the round's ruling.
    """

    prior: MetricRuling
    reply: MemberReply | MemberFailure
    readings: OrderReadings


@dataclass(frozen=True)
class MetricRound:
    """One metric put to every reachable member: what came back, and the ruling on it.

    `escalation` is None unless the council left the metric open and a model was
    named. `readings` holds both-order readings in roster order, empty where the
    run asked one order.
    """

    metric: str
    replies: tuple[MemberReply, ...]
    failures: tuple[MemberFailure, ...]
    ruling: MetricRuling
    escalation: MetricEscalation | None = None
    readings: tuple[OrderReadings, ...] = ()


@dataclass(frozen=True)
class CouncilRun:
    """One council over one advisory: every round, who was asked, who was not.

    `skipped` is the members never asked; `failures` is the calls that were made
    and gave nothing usable back. Different facts a report should not merge.
    """

    rounds: tuple[MetricRound, ...]
    asked: tuple[str, ...]
    skipped: tuple[SkippedMember, ...]
    single_assessor: bool

    @property
    def rulings(self) -> dict[str, MetricRuling]:
        """The rulings by metric, in the shape `chairman.agreed_vector` takes."""
        return {round_.metric: round_.ruling for round_ in self.rounds}

    @property
    def failures(self) -> tuple[MemberFailure, ...]:
        """Every call that was made and gave back nothing usable, across every metric."""
        return tuple(chain.from_iterable(round_.failures for round_ in self.rounds))
