"""Ask one model why a finding's published sources differ, keeping what it can quote.

One call per finding, carrying the disputed metrics and each source's value. An
item is kept when its metric is disputed, its `why` is non-empty, and its
quotation is in the advisory (the first such per metric); every other item is
recorded as dropped with the reason. The `why` is never checked, and nothing here
produces a number.
"""

from collections import Counter
from dataclasses import dataclass
from typing import Mapping

from council.evidence import is_quotation_from
from council.explanation_prompt import ExplanationPrompt, build_explanation_prompt
from council.explanation_reply import ExplanationItem, read_explanation
from council.providers import AskMember
from council.roster import Member
from council.transport import ModelUnavailable

# Why an item was not kept, the first that applies, in this order.
NOT_A_DISPUTED_METRIC = "not a disputed metric"
EMPTY_WHY = "empty why"
UNVERIFIED_QUOTATION = "unverified quotation"
REPEAT = "repeat"


@dataclass(frozen=True)
class DroppedItem:
    """An item that was not kept, and why.

    `quotation_found` is the quotation check's answer even for a dropped item: a
    repeat or an agreed metric can still quote the advisory exactly.
    """

    item: ExplanationItem
    reason: str
    quotation_found: bool


@dataclass(frozen=True)
class Explained:
    """An explanation kept: the items whose quotation is in the advisory, and those dropped."""

    model: str
    prompt_version: str
    items: tuple[ExplanationItem, ...]
    dropped: tuple[DroppedItem, ...]


@dataclass(frozen=True)
class NotExplained:
    """An explanation asked for and not kept, and why: failed, unreadable, or nothing kept."""

    model: str
    prompt_version: str
    because: str
    dropped: tuple[DroppedItem, ...] = ()


Explanation = Explained | NotExplained


def explain(
    advisory_text: str, published: Mapping[str, Mapping[str, str]],
    explainer: Member, clients: Mapping[str, AskMember],
) -> Explanation:
    """Ask one model why the sources differ on the disputed metrics, and keep what it can quote."""
    prompt = build_explanation_prompt(advisory_text, published)
    try:
        items = read_explanation(clients[explainer.provider](explainer, prompt))
    # ModelUnavailable is the server; ValueError is a reply that is not the shape asked for.
    except (ModelUnavailable, ValueError) as fault:
        return NotExplained(explainer.model, prompt.version, f"no readable explanation: {fault}")
    kept, dropped = sorted_out(items, prompt)
    if not kept:
        return NotExplained(explainer.model, prompt.version, none_kept(dropped), dropped)
    return Explained(explainer.model, prompt.version, kept, dropped)


def sorted_out(
    items: tuple[ExplanationItem, ...], prompt: ExplanationPrompt
) -> tuple[tuple[ExplanationItem, ...], tuple[DroppedItem, ...]]:
    """Keep the first good item on each disputed metric, and drop every other with its reason."""
    kept: dict[str, ExplanationItem] = {}
    dropped: list[DroppedItem] = []
    for item in items:
        reason = drop_reason(item, prompt, kept)
        if reason:
            found = is_quotation_from(item.quotation, prompt.advisory_shown)
            dropped.append(DroppedItem(item, reason, found))
            continue
        kept[item.metric] = item
    return tuple(kept.values()), tuple(dropped)


def drop_reason(
    item: ExplanationItem, prompt: ExplanationPrompt, kept: Mapping[str, ExplanationItem]
) -> str:
    """Say why an item is not kept, the first reason that applies, or nothing where it is kept."""
    if item.metric not in prompt.metrics:
        return NOT_A_DISPUTED_METRIC
    if not item.why:
        return EMPTY_WHY
    if not is_quotation_from(item.quotation, prompt.advisory_shown):
        return UNVERIFIED_QUOTATION
    if item.metric in kept:
        return REPEAT
    return ""


def none_kept(dropped: tuple[DroppedItem, ...]) -> str:
    """Say why nothing was kept: no item offered, or every one dropped, counted by reason."""
    if not dropped:
        return "the model offered no item"
    items = "item" if len(dropped) == 1 else "items"
    reasons = Counter(one.reason for one in dropped)
    counted = ", ".join(f"{reason} {count}" for reason, count in sorted(reasons.items()))
    return f"the model offered {len(dropped)} {items}, and none was kept ({counted})"
