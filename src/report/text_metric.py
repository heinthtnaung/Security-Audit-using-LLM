"""One metric the council did not settle, as the terminal shows it: every model that spoke to it.

Shows each member's value, confidence, whether its quotation was found in the advisory, and the
quotation in full, then the escalation model where one was asked. The quotation is re-flowed to
the page, never shortened: on a contested metric it is the disagreement.
"""

from itertools import chain

from report.council_record import MemberSaid, MetricRuling, SaidKind
from report.council_words import (
    chairman_said,
    checked,
    confident,
    counted,
    declined_one_way,
    escalated_who,
    outcome_said,
    same_evidence_said,
    unanswered,
    who,
)
from report.text_layout import SOURCE_SEPARATOR, indented, wrapped

# The depths the council block indents to, named because four of them read as arithmetic.
ADVISORY_DEPTH = 1
METRIC_DEPTH = 2
MEMBER_DEPTH = 3
QUOTATION_DEPTH = 4
# Typographic marks, so an apostrophe or straight quote inside the quotation is not mistaken.
OPEN_QUOTE = "“"
CLOSE_QUOTE = "”"


def ruling_lines(ruling: MetricRuling) -> list[str]:
    """Give one unsettled metric, what the chairman made of it, and every member behind it."""
    spoke = counted(len(ruling.said), "member")
    said = SOURCE_SEPARATOR.join([ruling.metric, outcome_said(ruling), spoke])
    return [
        indented(METRIC_DEPTH, said),
        *[indented(MEMBER_DEPTH, one) for one in same_evidence_said(ruling)],
        *chairman_lines(ruling),
        *chain.from_iterable(member_lines(one) for one in ruling.said),
        *escalation_lines(ruling),
    ]


def chairman_lines(ruling: MetricRuling) -> list[str]:
    """Give what the chairman decided and why, where it decided anything at all."""
    told = chairman_said(ruling)
    return [indented(MEMBER_DEPTH, SOURCE_SEPARATOR.join(told))] if told else []


def escalation_lines(ruling: MetricRuling) -> list[str]:
    """Give what the escalation model said of a metric, below the members, where it was asked."""
    if ruling.escalation is None:
        return []
    said = ruling.escalation.said
    return said_lines(escalated_who(said.member), said)


def member_lines(said: MemberSaid) -> list[str]:
    """Give one member's answer, what it was worth to it, and its quotation in full."""
    return said_lines(who(said.member), said)


def said_lines(named: str, said: MemberSaid) -> list[str]:
    """Give one model's answer under the name it is listed by, and its quotation in full."""
    if said.kind is not SaidKind.ANSWERED:
        unsaid = SOURCE_SEPARATOR.join([unanswered(said), *declined_one_way(said)])
        return [indented(MEMBER_DEPTH, f"{named}  {unsaid}")]
    answered = SOURCE_SEPARATOR.join(
        [said.value, confident(said.confidence), checked(said.verified), *declined_one_way(said)]
    )
    return [
        indented(MEMBER_DEPTH, f"{named}  {answered}"),
        *evidence_lines(said.evidence),
    ]


def evidence_lines(quotation: str) -> list[str]:
    """Quote a member's evidence whole, re-flowed to the page rather than shortened."""
    if not quotation:
        return []
    folded = " ".join(quotation.split())
    return wrapped(f"{OPEN_QUOTE}{folded}{CLOSE_QUOTE}", QUOTATION_DEPTH)
