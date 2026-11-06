"""Saying a council run is alive, on the error stream and never on stdout.

A long run makes hundreds of sequential model calls, and the silence is
indistinguishable from a hang. Never stdout, which carries the record and must stay
byte-identical. A terminal gets a bar redrawn in place (`cli.progress_bar`); a
redirected stream and `--debug` get one line per call. Counts, not timings: there is
no clock anywhere in `src/`.
"""

from dataclasses import dataclass, field
from typing import TextIO

from cli.progress_bar import BarDisplay, bar_for

METRICS_PER_FINDING = 8
# How many times each member is asked each metric: in the options' order, and reversed.
BOTH_ORDERS = 2
ONE_ORDER = 1
# Said after the metric on a reversed call, so its line is not the in-order call's twice.
REVERSED_LABEL = " (options reversed)"
COUNCIL_LINE = "council"
# Counted apart: a run's escalation count is unknown until the council leaves something open.
ESCALATION_LINE = "escalation"
# One call per finding whose sources disagree, made once the council is done.
EXPLANATION_LINE = "explanation"


@dataclass
class CouncilProgress:
    """How far a council run has got, said on the error stream as it goes."""

    # Mutable, unlike the rest here: counting is state.
    findings: int
    members: int
    out: TextIO
    # Each metric asked in the options' order and reversed, where the run checks both.
    orders: int = ONE_ORDER
    # The log is the default; `--debug` keeps it even at a terminal, where a bar is drawn instead.
    debug: bool = False
    asked: int = field(default=0, init=False)
    escalated: int = field(default=0, init=False)
    reached: int = field(default=0, init=False)
    advisory_id: str = field(default="", init=False)
    bar: BarDisplay | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        """Choose the display once the stream is known: a bar on a terminal, else the log."""
        self.bar = bar_for(self.out, self.debug)

    @property
    def calls(self) -> int:
        """Give how many model calls the whole run will make."""
        return self.findings * METRICS_PER_FINDING * self.members * self.orders

    def starting(self, advisory_id: str) -> None:
        """Note that the council has moved on to another advisory."""
        self.reached += 1
        self.advisory_id = advisory_id

    def returning_to(self, position: int, advisory_id: str) -> None:
        """Note that escalation has come back to an advisory the council read earlier in the run."""
        # Set, not counted: the council reached it already, at this place among the findings.
        self.reached = position
        self.advisory_id = advisory_id

    def asking(self, metric: str, member: str, reversed_options: bool = False) -> None:
        """Say which member is about to be asked which metric, and in which order, before it is."""
        self.asked += 1
        if self.bar is not None:
            self.bar.council(COUNCIL_LINE, self.asked, self.calls, self.reached, self.findings)
            return
        self.say(f"{COUNCIL_LINE} {self.asked}/{self.calls}", metric, member, reversed_options)

    def escalating(self, metric: str, member: str, reversed_options: bool = False) -> None:
        """Say which metric the escalation model is about to be asked, and in which order."""
        self.escalated += 1
        if self.bar is not None:
            self.bar.escalation(
                ESCALATION_LINE, self.escalated, self.reached, self.findings, self.advisory_id
            )
            return
        self.say(f"{ESCALATION_LINE} {self.escalated}", metric, member, reversed_options)

    def finish(self) -> None:
        """Close the bar's line so later output starts fresh; nothing to do for the log."""
        if self.bar is not None:
            self.bar.finish()

    def say(self, counted: str, metric: str, member: str, reversed_options: bool) -> None:
        """Write the line for one call about to be made, flushed so it shows before the call."""
        order = REVERSED_LABEL if reversed_options else ""
        self.out.write(
            f"{counted}  finding {self.reached}/{self.findings} {self.advisory_id}  "
            f"{metric}{order}  {member}\n"
        )
        self.out.flush()


@dataclass(frozen=True)
class NoProgress:
    """Say nothing, which is what a run with nothing slow in it needs."""

    def starting(self, advisory_id: str) -> None:
        """Note nothing."""

    def returning_to(self, position: int, advisory_id: str) -> None:
        """Note nothing."""

    def asking(self, metric: str, member: str, reversed_options: bool = False) -> None:
        """Say nothing."""

    def escalating(self, metric: str, member: str, reversed_options: bool = False) -> None:
        """Say nothing."""

    def finish(self) -> None:
        """Note nothing."""


NO_PROGRESS = NoProgress()


@dataclass
class ExplanationProgress:
    """How far the explanations have got, said on the error stream before each call."""

    findings: int
    out: TextIO
    # The log is the default; `--debug` keeps it even at a terminal, where a bar is drawn instead.
    debug: bool = False
    asked: int = field(default=0, init=False)
    bar: BarDisplay | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        """Choose the display once the stream is known: a bar on a terminal, else the log."""
        self.bar = bar_for(self.out, self.debug)

    def explaining(self, advisory_id: str, model: str) -> None:
        """Say which finding the explainer is about to be asked about, before it is."""
        self.asked += 1
        if self.bar is not None:
            self.bar.explanation(EXPLANATION_LINE, self.asked, self.findings, advisory_id)
            return
        self.out.write(
            f"{EXPLANATION_LINE} {self.asked}/{self.findings}  finding {advisory_id}  {model}\n"
        )
        self.out.flush()

    def finish(self) -> None:
        """Close the bar's line so later output starts fresh; nothing to do for the log."""
        if self.bar is not None:
            self.bar.finish()


@dataclass(frozen=True)
class NoExplanationProgress:
    """Say nothing about explanations, which is what a run nobody is watching needs."""

    def explaining(self, advisory_id: str, model: str) -> None:
        """Say nothing."""

    def finish(self) -> None:
        """Note nothing."""


NO_EXPLANATION_PROGRESS = NoExplanationProgress()


def orders_asked(order_check: bool) -> int:
    """Give how many times each member is asked each metric, once or in both orders."""
    return BOTH_ORDERS if order_check else ONE_ORDER
