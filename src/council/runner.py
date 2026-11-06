"""Put one advisory to the roster, member by member, and collect the rulings.

This dispatches; `chairman.rule_on_metric` decides, and no number appears here. A
member is only ever shown the redacted advisory, and a member nothing can reach is
kept on the record rather than dropped. A failed call costs that one metric, not
the run. One member answers every metric before the next is asked, because local
members share one Ollama server and swapping models is slow. What the council
leaves open may then go to one escalation model (`council.escalation`).
"""

from typing import Callable, Mapping

from council.answer import MemberReply
from council.chairman import rule_on_metric
from council.order_check import reconciled
from council.prompt import MemberPrompt, build_prompt
from council.providers import PROVIDER_CLIENTS, AskMember, reachable_members, unreachable_members
from council.reply import read_reply
from council.roster import Member, Roster, members_to_ask
from council.ruling import Fallback
from council.run import CouncilRun, MemberFailure, MetricRound, OrderReadings
from council.transport import ModelUnavailable
from cvss.metrics import METRIC_ORDER

# What one call to one member gave back.
CallOutcome = MemberReply | MemberFailure
# What one member gave back on one metric: one call's outcome, or both orders' readings.
Asked = CallOutcome | OrderReadings


def nobody_asking(metric: str, member: str, reversed_options: bool = False) -> None:
    """Report nothing, which is what a run nobody is watching needs."""


def assess(
    advisory_text: str,
    roster: Roster,
    fallbacks: Mapping[str, Fallback],
    clients: Mapping[str, AskMember] = PROVIDER_CLIENTS,
    asking: Callable[[str, str, bool], None] = nobody_asking,
    order_check: bool = False,
) -> CouncilRun:
    """Put one advisory to the roster, one member at a time, and rule on every metric.

    With `order_check`, a value counts only where both orders give it (`council.order_check`).
    """
    refuse_incomplete_fallbacks(fallbacks)
    reachable = reachable_members(members_to_ask(roster), clients)
    prompts = prompts_of(advisory_text)
    reversed_prompts = prompts_of(advisory_text, reversed_options=True) if order_check else ()
    answered = [
        ask_every_metric(member, prompts, clients, asking, reversed_prompts)
        for member in reachable
    ]
    rounds = [rule_on_round(prompt, answered, fallbacks[prompt.metric]) for prompt in prompts]
    return CouncilRun(
        rounds=tuple(rounds),
        asked=tuple(member.name for member in reachable),
        skipped=unreachable_members(roster, clients),
        # Counted from who was actually asked, not from the roster.
        single_assessor=len(reachable) == 1,
    )


def prompts_of(advisory_text: str, reversed_options: bool = False) -> tuple[MemberPrompt, ...]:
    """Build every metric's prompt for one advisory, with its options in order or reversed."""
    return tuple(build_prompt(metric, advisory_text, reversed_options) for metric in METRIC_ORDER)


def ask_every_metric(
    member: Member,
    prompts: tuple[MemberPrompt, ...],
    clients: Mapping[str, AskMember],
    asking: Callable[[str, str, bool], None] = nobody_asking,
    reversed_prompts: tuple[MemberPrompt, ...] = (),
) -> dict[str, Asked]:
    """Put every metric's prompt to one member, in both orders if asked, and give its readings."""
    if not reversed_prompts:
        return {one.metric: ask_one_member(member, one, clients, asking) for one in prompts}
    return {
        prompt.metric: OrderReadings(
            ask_one_member(member, prompt, clients, asking),
            ask_one_member(member, reversed_prompt, clients, asking, reversed_options=True),
        )
        for prompt, reversed_prompt in zip(prompts, reversed_prompts, strict=True)
    }


def rule_on_round(
    prompt: MemberPrompt, answered: list[dict[str, Asked]], fallback: Fallback
) -> MetricRound:
    """Gather every member's outcome on one metric, in roster order, and rule on it."""
    asked = [by_metric[prompt.metric] for by_metric in answered]
    outcomes = [outcome_of(one) for one in asked]
    replies = tuple(item for item in outcomes if not isinstance(item, MemberFailure))
    return MetricRound(
        metric=prompt.metric,
        replies=replies,
        failures=tuple(item for item in outcomes if isinstance(item, MemberFailure)),
        # The redacted text the member read, never the raw advisory.
        ruling=rule_on_metric(prompt.metric, replies, prompt.advisory_shown, fallback),
        readings=tuple(one for one in asked if isinstance(one, OrderReadings)),
    )


def outcome_of(asked: Asked) -> CallOutcome:
    """Give one member's one outcome on a metric, its two readings made one where it has two."""
    if isinstance(asked, OrderReadings):
        return reconciled(asked.in_order, asked.reversed_order)
    return asked


def ask_one_member(
    member: Member,
    prompt: MemberPrompt,
    clients: Mapping[str, AskMember],
    asking: Callable[[str, str, bool], None] = nobody_asking,
    reversed_options: bool = False,
) -> CallOutcome:
    """Put one prompt to one member, recording a failure rather than ending the run."""
    # Reported before the call, so a slow member shows as a pending line.
    asking(prompt.metric, member.name, reversed_options)
    who = member.identify(prompt.version)
    try:
        said = clients[member.provider](member, prompt)
        return read_reply(said, prompt.metric, who)
    # ModelUnavailable is the server; ValueError is an unreadable or illegal reply.
    except (ModelUnavailable, ValueError) as fault:
        return MemberFailure(member=who, metric=prompt.metric, reason=str(fault))


def refuse_incomplete_fallbacks(fallbacks: Mapping[str, Fallback]) -> None:
    """Refuse a run without a fallback ready for every metric, before any model is asked."""
    # Which source a fallback comes from is the caller's to decide.
    if not isinstance(fallbacks, Mapping):
        raise TypeError(
            f"Fallbacks must be a mapping of metric to fallback, "
            f"not {type(fallbacks).__name__}"
        )
    missing = [metric for metric in METRIC_ORDER if metric not in fallbacks]
    if missing:
        raise ValueError(f"No fallback ready for {', '.join(missing)}; supply one for each metric")
