"""Send the metrics a council left open to one Ollama model, in both orders.

Only a metric still contested or unresolved after the order check is sent, never
the whole advisory. The model is named by `AUDITOR_ESCALATION_MODEL`, runs on the
members' server, and is not itself a member; a hosted one, or one on the council,
is refused. It is asked each metric in both orders like a member; the chairman
(`rule_on_escalation`) decides what its reply is worth.
"""

from dataclasses import replace
from typing import Callable, Mapping

from council.chairman import rule_on_escalation
from council.order_check import reconciled
from council.prompt import build_prompt
from council.providers import AskMember
from council.roster import Member
from council.ruling import SettledMetric
from council.run import CouncilRun, MetricEscalation, MetricRound, OrderReadings
from council.runner import ask_one_member, nobody_asking


def escalate(
    run: CouncilRun, advisory_text: str, escalation: Member | None,
    clients: Mapping[str, AskMember], asking: Callable[[str, str, bool], None] = nobody_asking,
) -> CouncilRun:
    """Put every metric the council left open to the escalation model; with none, change nothing."""
    if escalation is None:
        return run
    refuse_unfit_escalation(escalation, run.asked, clients)
    rounds = [escalated(one, advisory_text, escalation, clients, asking) for one in run.rounds]
    return replace(run, rounds=tuple(rounds))


def escalated(
    round_: MetricRound, advisory_text: str, escalation: Member,
    clients: Mapping[str, AskMember], asking: Callable[[str, str, bool], None],
) -> MetricRound:
    """Leave a settled metric as it is, and put an open one to the escalation model."""
    if isinstance(round_.ruling, SettledMetric):
        return round_
    in_order = build_prompt(round_.metric, advisory_text)
    reversed_order = build_prompt(round_.metric, advisory_text, reversed_options=True)
    readings = OrderReadings(
        ask_one_member(escalation, in_order, clients, asking),
        ask_one_member(escalation, reversed_order, clients, asking, reversed_options=True),
    )
    reply = reconciled(readings.in_order, readings.reversed_order)
    # The redacted text the model read, which its quotation must appear in.
    ruling = rule_on_escalation(round_.ruling, reply, in_order.advisory_shown)
    asked = MetricEscalation(round_.ruling, reply, readings)
    return replace(round_, ruling=ruling, escalation=asked)


def refuse_unfit_escalation(
    escalation: Member | None, council: tuple[str, ...], clients: Mapping[str, AskMember]
) -> None:
    """Refuse an escalation model that is hosted, sits on the council, or has no client here."""
    if escalation is None:
        return
    if escalation.is_hosted():
        raise ValueError(
            f"{escalation.name} is hosted; the escalation model runs on the members' Ollama server"
        )
    if escalation.name in council:
        raise ValueError(
            f"{escalation.name} is on the council, so it cannot also be the model "
            "the council's open metrics escalate to"
        )
    if escalation.provider not in clients:
        raise ValueError(
            f"no client for provider {escalation.provider!r} reaches {escalation.name}"
        )
