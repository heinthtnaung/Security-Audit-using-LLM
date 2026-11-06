"""The approved question library: the only questions an assessment may be scored from.

A caller answers by question id, resolved against this file, so nothing outside it
can introduce a question or change what a Yes is worth. Three categories; technical
severity comes from the CVSS vectors and is not asked. The exposure weights are
quoted from the design; the business and threat weights are this file's own.
"""

from types import MappingProxyType
from typing import Mapping

from scoring.question import Answer, Category, Question

# From docs/SCORING_MODEL.md, quoted weight for weight.
EXPOSURE_QUESTIONS: tuple[Question, ...] = (
    Question("EXP-1", "Is the affected service internet-facing?", Category.EXPOSURE, 40),
    Question("EXP-2", "Is it reachable from an untrusted network?", Category.EXPOSURE, 25),
    Question("EXP-3", "Is the vulnerable port or API exposed?", Category.EXPOSURE, 20),
    Question("EXP-4", "Is the asset isolated or segmented?", Category.EXPOSURE, -15),
    Question("EXP-5", "Is the component disabled?", Category.EXPOSURE, -30),
)

# This file's own; sums to the 80 the design's worked example prints.
BUSINESS_QUESTIONS: tuple[Question, ...] = (
    Question("BUS-1", "Is the asset business-critical?", Category.BUSINESS, 40),
    Question("BUS-2", "Is it running in production?", Category.BUSINESS, 20),
    Question("BUS-3", "Does it hold sensitive or regulated data?", Category.BUSINESS, 20),
    Question("BUS-4", "Would an outage halt a business process?", Category.BUSINESS, 20),
)

# This file's own; the design's three threat facts in descending weight.
THREAT_QUESTIONS: tuple[Question, ...] = (
    Question("THR-1", "Is this vulnerability being exploited in the wild?", Category.THREAT, 50),
    Question("THR-2", "Is public exploit code available?", Category.THREAT, 30),
    Question("THR-3", "Is exploitation automated by worms or scanners?", Category.THREAT, 20),
)

APPROVED_QUESTIONS: tuple[Question, ...] = (
    EXPOSURE_QUESTIONS + BUSINESS_QUESTIONS + THREAT_QUESTIONS
)

# Locked, so nothing outside can add a question by assigning into it.
QUESTIONS_BY_ID: Mapping[str, Question] = MappingProxyType(
    {asked.question_id: asked for asked in APPROVED_QUESTIONS}
)

ANSWERED_CATEGORIES: tuple[Category, ...] = (
    Category.EXPOSURE,
    Category.BUSINESS,
    Category.THREAT,
)


def question(identifier: str) -> Question:
    """Give one approved question by its id, refusing one nobody approved."""
    asked = QUESTIONS_BY_ID.get(identifier)
    if asked is None:
        raise ValueError(f"{identifier!r} is not a question in the approved library")
    return asked


def questions_of(category: Category) -> tuple[Question, ...]:
    """Give the approved questions of one category, in the order the library lists them."""
    refuse_unanswerable_category(category)
    return tuple(asked for asked in APPROVED_QUESTIONS if asked.category is category)


def answers_for(
    category: Category, answers_by_id: Mapping[str, Answer]
) -> dict[Question, Answer]:
    """Resolve answers given by id into the approved questions of one category."""
    # A caller answers by id and never holds a Question, so it cannot reweigh one.
    refuse_unanswerable_category(category)
    return {
        question(identifier): answer
        for identifier, answer in answers_by_id.items()
        if question(identifier).category is category
    }


def refuse_incomplete(answers_by_id: Mapping[str, Answer]) -> None:
    """Refuse an answer set that leaves an approved question unanswered."""
    # The library is fixed, so a complete set is well defined and an omission is
    # malformed input. Answering Unknown is how to record that nobody knows.
    missing = [
        asked.question_id
        for asked in APPROVED_QUESTIONS
        if asked.question_id not in answers_by_id
    ]
    if not missing:
        return
    raise ValueError(
        f"{', '.join(missing)} unanswered; the approved library asks all "
        f"{len(APPROVED_QUESTIONS)}. An omission is not an answer -- answer "
        "Unknown to record that nobody knows, and the score comes out flagged."
    )


def refuse_unanswerable_category(category: Category) -> None:
    """Refuse a category nobody is asked about, which is technical severity."""
    if category in ANSWERED_CATEGORIES:
        return
    raise ValueError(
        f"{category.value} is not asked of an organisation; it comes from the published vectors"
    )
