"""The field names a member's reply uses, stated once for prompt and parser.

`council.prompt` asks for exactly these and `council.reply` reads exactly these,
so the two cannot drift apart.
"""

from council.answer import Confidence

VALUE_FIELD = "value"
EVIDENCE_FIELD = "evidence"
CONFIDENCE_FIELD = "confidence"

REQUIRED_FIELDS: tuple[str, ...] = (VALUE_FIELD, EVIDENCE_FIELD, CONFIDENCE_FIELD)

# Not asked for; models add it anyway. A reply naming another metric answered a
# different question.
METRIC_FIELD = "metric"

# A word, not a letter, so it never collides with a Base metric value.
NO_EVIDENCE_VALUE = "NO_EVIDENCE"

CONFIDENCE_BY_WORD: dict[str, Confidence] = {level.value: level for level in Confidence}

CONFIDENCE_WORDS: tuple[str, ...] = tuple(CONFIDENCE_BY_WORD)
