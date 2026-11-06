"""One metric the council could not settle, opened to every member behind it.

Shows each member's value, confidence, whether its quotation was found in the advisory, and
the quotation in full -- on a contested metric the quotation is the disagreement. Any
escalation reply follows. Shared wording is in `report.council_words`.
"""

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
from report.html_layout import listing, separated, tag, text

# Marked, because an unverified quotation must not read as a verified one.
UNVERIFIED_CLASS = "unverified"
VERIFIED_CLASS = "verified"


def metric_details(ruling: MetricRuling) -> str:
    """Give one unsettled metric: what the chairman made of it, then every member."""
    headed = tag("summary", metric_summary(ruling))
    spoke = chairman_line(ruling) + members(ruling.said) + escalation(ruling)
    return tag("details", headed + spoke, "metric")


def metric_summary(ruling: MetricRuling) -> str:
    """Head the disclosure with the metric, its outcome, and how many spoke to it."""
    named = tag("code", text(ruling.metric))
    headed = [named, text(outcome_said(ruling)), text(counted(len(ruling.said), "member"))]
    flags = [tag("span", text(one), "flag") for one in same_evidence_said(ruling)]
    return separated([*headed, *flags])


def chairman_line(ruling: MetricRuling) -> str:
    """Give what the chairman decided and why."""
    told = separated([text(one) for one in chairman_said(ruling)])
    return tag("p", told, "ruling") if told else ""


def members(said: tuple[MemberSaid, ...]) -> str:
    """Put every member that spoke to one metric on a row of its own."""
    return listing([member_row(one) for one in said], "members")


def escalation(ruling: MetricRuling) -> str:
    """List what the escalation model said of a metric, below the members, where it was asked."""
    if ruling.escalation is None:
        return ""
    said = ruling.escalation.said
    # Styled as the members are, and marked apart from them.
    return listing([said_row(escalated_who(said.member), said)], "members escalation")


def member_row(said: MemberSaid) -> str:
    """Give one member's answer, what it was worth to it, and its quotation in full."""
    return said_row(who(said.member), said)


def said_row(name: str, said: MemberSaid) -> str:
    """Give one model's answer under the name it is listed by, and its quotation in full."""
    named = tag("span", text(name), "member-name")
    if said.kind is not SaidKind.ANSWERED:
        return named + separated([tag("span", text(unanswered(said)), "refusal"), *one_way(said)])
    answered = [
        tag("span", text(said.value), "member-value"),
        text(confident(said.confidence)),
        checked_mark(said.verified),
        *one_way(said),
    ]
    return named + separated(answered) + evidence(said.evidence)


def one_way(said: MemberSaid) -> list[str]:
    """Mark the order a member declined in, where the other order did not."""
    return [tag("span", text(one), "refusal") for one in declined_one_way(said)]


def checked_mark(verified: bool) -> str:
    """Mark whether a quotation was found in the advisory."""
    marked = VERIFIED_CLASS if verified else UNVERIFIED_CLASS
    return tag("span", text(checked(verified)), marked)


def evidence(quotation: str) -> str:
    """Quote a member's evidence in full, because on a contested metric it is the argument."""
    if not quotation:
        return ""
    return tag("blockquote", text(quotation), "evidence")
