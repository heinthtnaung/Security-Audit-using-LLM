"""Every term behind one finding's scores, collapsed in a `<details>` until a reader asks.

Each answer is shown with its weight and contribution, so the number re-derives by hand.
All four answers appear as given; Unknown is marked, since it is what makes a score
provisional. Categories are written once per finding; only the technical term moves per source.
"""

from report.html_layout import listing, number, tag, text
from scoring.question import Answer
from scoring.risk_score import RiskScore

DERIVATION_SUMMARY = "How this number was reached"
WEIGHTING_LABEL = "Weighted"
TECHNICAL_LABEL = "technical"
UNKNOWN_CLASS = "answer-value flag"
ANSWER_CLASS = "answer-value"


def derivation(weighed) -> str:
    """Show every term behind one finding's scores, collapsed until a reader asks."""
    # Categories and weighting are the same on every score; only the technical term differs.
    scored = weighed.scores[0]
    behind = technical_list(weighed) + category_blocks(scored) + weighting(scored)
    return tag("details", tag("summary", text(DERIVATION_SUMMARY)) + behind)


def weighting(scored: RiskScore) -> str:
    """Give the weighting that combined the categories, which the total alone does not show."""
    named = ", ".join(f"{one.category} {number(one.weight)}" for one in scored.weights)
    return tag("p", text(f"{WEIGHTING_LABEL} {named}."), "weighting")


def technical_list(weighed) -> str:
    """Give the technical term each source contributed, the one term that moves."""
    return listing([technical_row(one) for one in weighed.scores], "answers")


def technical_row(scored) -> str:
    """Give one source's technical severity on the 0-100 category scale."""
    return (
        tag("span", text(TECHNICAL_LABEL), "answer-id")
        + tag("span", text(technical_sentence(scored.technical)), "answer-text")
        + tag("span", text(f"{number(scored.technical_score)} of 100"), ANSWER_CLASS)
    )


def technical_sentence(technical) -> str:
    """Say where a technical severity came from, including when nobody offered one."""
    return getattr(technical, "derived_from", None) or technical.reason


def category_blocks(scored) -> str:
    """Give every category this organisation was asked about, in the engine's own order."""
    asked = (scored.exposure, scored.business, scored.threat)
    return "".join(category_block(one) for one in asked)


def category_block(category) -> str:
    """Give one category's score, its raw total, and every answer behind it."""
    named = tag("span", text(category.category.value), "category-name")
    total = tag("span", text(category_total(category)), "category-total")
    answers = listing([answer_row(one) for one in category.answers], "answers")
    return tag("div", tag("p", f"{named} {total}") + answers, "category")


def category_total(category) -> str:
    """Say what a category scored, what it totalled before the clamp, and whether it was held."""
    # Show the raw total too: the clamp is invisible in the score alone.
    held = ", clamped" if category.was_clamped else ""
    return f"{number(category.score)} of 100 (raw total {number(category.raw_total)}{held})"


def answer_row(answered) -> str:
    """Give one answer, the question it answers, and what that answer was worth."""
    worth = (
        f"yes {number(answered.question.yes_weight)}, "
        f"contributed {number(answered.contribution)}"
    )
    return (
        tag("span", text(answered.question.question_id), "answer-id")
        + tag("span", text(answered.question.text), "answer-text")
        + tag("span", text(answered.answer.value), answer_class(answered.answer))
        + tag("span", text(worth), "answer-weight")
    )


def answer_class(answer) -> str:
    """Mark an Unknown answer, which is the one that leaves a score provisional."""
    return UNKNOWN_CLASS if answer is Answer.UNKNOWN else ANSWER_CLASS
