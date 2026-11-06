"""What the organisation answered, read from a JSON file the operator fills in.

Default answers apply to every finding, and an advisory may override them. An
unknown key is ignored, which is how the example file carries each question's text
under `_questions`. An answer is Yes, No, Unknown or N/A; Unknown is carried
through, never read as No. A file that omits a question is refused.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from scoring.library import question, refuse_incomplete
from scoring.question import Answer

ANSWERS_FIELD = "answers"
BY_ADVISORY_FIELD = "by_advisory"
APPROVAL_FIELD = "approval"

ANSWERS_BY_WORD = {given.value.lower(): given for given in Answer}


@dataclass(frozen=True)
class OrganisationAnswers:
    """One environment's answers: what holds everywhere, and what one advisory changes."""

    everywhere: Mapping[str, Answer] = field(default_factory=dict)
    by_advisory: Mapping[str, Mapping[str, Answer]] = field(default_factory=dict)

    def applying_to(self, advisory_id: str) -> dict[str, Answer]:
        """Give the answers that apply to one advisory, its own overriding the default."""
        return {**self.everywhere, **self.by_advisory.get(advisory_id, {})}


def read_answers(path: str | Path) -> OrganisationAnswers:
    """Read an answer file, refusing anything the approved library does not recognise."""
    document = read_document(Path(path))
    everywhere = read_block(document.get(ANSWERS_FIELD) or {}, ANSWERS_FIELD)
    refuse_incomplete(everywhere)
    return OrganisationAnswers(
        everywhere=everywhere,
        by_advisory={
            advisory_id: read_block(block, f"{BY_ADVISORY_FIELD}.{advisory_id}")
            for advisory_id, block in (document.get(BY_ADVISORY_FIELD) or {}).items()
        },
    )


def read_document(path: Path) -> Mapping[str, Any]:
    """Read the file, refusing one that is absent or is not the JSON object it must be."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except OSError as fault:
        raise ValueError(f"No answer file at {str(path)!r}: {fault}") from fault
    except ValueError as fault:
        raise ValueError(f"{str(path)!r} is not readable JSON: {fault}") from fault
    if not isinstance(document, Mapping):
        raise ValueError(f"{str(path)!r} must hold a JSON object of answers")
    return document


def read_block(block: Any, named: str) -> dict[str, Answer]:
    """Read one block of answers, resolving every id against the approved library."""
    if not isinstance(block, Mapping):
        raise ValueError(f"{named} must be an object of question id to answer")
    return {identifier: read_one(identifier, given, named) for identifier, given in block.items()}


def read_one(identifier: str, given: Any, named: str) -> Answer:
    """Read one answer, refusing a question nobody approved and a word nobody offered."""
    # Resolving through the library stops a file inventing a question or a weight.
    question(identifier)
    answer = ANSWERS_BY_WORD.get(str(given).strip().lower())
    if answer is None:
        allowed = ", ".join(one.value for one in Answer)
        raise ValueError(f"{named}.{identifier} is {given!r}; an answer is {allowed}")
    return answer


def approval_block(path: str | Path) -> Mapping[str, Any]:
    """Give the approval an answer file carries, which is empty when it carries none."""
    block = read_document(Path(path)).get(APPROVAL_FIELD) or {}
    if not isinstance(block, Mapping):
        raise ValueError(f"{APPROVAL_FIELD} must be an object naming who approved and when")
    return block
