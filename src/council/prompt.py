"""What one member is asked about one metric, and the version of the asking.

One metric at a time, with that metric's definition in the system turn and the
redacted advisory alone in the user turn. A verbatim quotation is asked for, and
declining is named as better than inventing one. `PROMPT_VERSION` rides on every
answer; bump it whenever the wording below changes, and a test catches a change
that moves without it. The reversed-options prompt is `REVERSED_PROMPT_VERSION`.
"""

import json
from dataclasses import dataclass

from council.definitions import definition_of
from council.redaction import redact
from council.reply_format import (
    CONFIDENCE_FIELD,
    CONFIDENCE_WORDS,
    EVIDENCE_FIELD,
    NO_EVIDENCE_VALUE,
    VALUE_FIELD,
)
from cvss.metrics import metric_name

PROMPT_VERSION = "member-base-metric-3"
REVERSED_PROMPT_VERSION = "member-base-metric-3+reversed-1"

SCHEMA_INDENT = 2

SYSTEM_TEMPLATE = f"""\
You assess one metric of the CVSS v3.1 Base score from the text of a security
advisory, and from nothing else.

You are one of several assessors reading this advisory independently. You will
not see what the others answered, and you must not guess at it.

The metric you are assessing, and what its values mean:

{{description}}

{{values}}

That definition is reference material. It is not the advisory and you may not
quote it.

- Decide only this metric. Say nothing about the others.
- Judge from the advisory text in the next message. Do not use anything you may
  remember about this vulnerability from elsewhere.
- Support your value with a quotation copied word for word from that advisory.
  Inventing a quotation is worse than declining: application code checks it
  against the advisory, and an invented or reworded one is thrown out.
- If the advisory says nothing that supports any value, answer {NO_EVIDENCE_VALUE}.
  Declining is a correct answer. Guessing is not.
- Reply with one JSON object and nothing else.
"""

USER_TEMPLATE = """\
{advisory}

Reply with one JSON object of exactly these three fields:

{schema}
"""


@dataclass(frozen=True)
class MemberPrompt:
    """One question to one member: what it was asked, and exactly what it was shown.

    `advisory_shown` is the redacted text the member read, also what its quotation
    is checked against. `withheld` is everything `council.redaction` took out, in
    the order the patterns ran, with a repeat listed each time.
    """

    metric: str
    system: str
    user: str
    advisory_shown: str
    withheld: tuple[str, ...]
    version: str

    @property
    def subject(self) -> str:
        """Name the metric asked about, as a refusal of this prompt says it."""
        return self.metric


def build_prompt(metric: str, advisory_text: str, reversed_options: bool = False) -> MemberPrompt:
    """Build the prompt asking one member for one metric of one advisory, in either order."""
    advisory = redact(advisory_text)
    return MemberPrompt(
        metric=metric,
        system=system_prompt(metric, reversed_options),
        user=user_prompt(metric, advisory.text, reversed_options),
        advisory_shown=advisory.text,
        withheld=advisory.removed,
        version=REVERSED_PROMPT_VERSION if reversed_options else PROMPT_VERSION,
    )


def system_prompt(metric: str, reversed_options: bool = False) -> str:
    """Render the standing instruction: the rules, the metric, and what its values mean."""
    lines = value_lines(metric, reversed_options)
    return SYSTEM_TEMPLATE.format(description=describe(metric), values="\n".join(lines))


def user_prompt(metric: str, advisory_text: str, reversed_options: bool = False) -> str:
    """Render the turn the member answers: the advisory, and the shape of a reply."""
    schema = reply_schema(metric, reversed_options)
    return USER_TEMPLATE.format(advisory=advisory_text.strip(), schema=schema)


def describe(metric: str) -> str:
    """Say in one line what a metric measures, naming it in words as well as letters."""
    return f"{metric_name(metric)} ({metric}) measures {definition_of(metric).measures}"


def value_lines(metric: str, reversed_options: bool = False) -> tuple[str, ...]:
    """List a metric's values as 'X = what it means' lines, in specification order or reversed."""
    meanings = definition_of(metric).value_meanings
    lines = tuple(f"{value} = {meaning}" for value, meaning in meanings.items())
    return listed(lines, reversed_options)


def listed(options: tuple[str, ...], reversed_options: bool) -> tuple[str, ...]:
    """Give a metric's options in specification order, or the other way round."""
    return options[::-1] if reversed_options else options


def reply_schema(metric: str, reversed_options: bool = False) -> str:
    """Show the three fields a reply must carry and what each may hold, for this metric."""
    allowed = ", ".join(listed(tuple(definition_of(metric).value_meanings), reversed_options))
    return json.dumps(
        {
            VALUE_FIELD: (
                f"one of {allowed} -- or {NO_EVIDENCE_VALUE} "
                "if the advisory supports none of them"
            ),
            EVIDENCE_FIELD: (
                "a quotation copied word for word from the advisory above, "
                "never from the metric definition -- "
                f"or an empty string if you answered {NO_EVIDENCE_VALUE}"
            ),
            CONFIDENCE_FIELD: f"one of {', '.join(CONFIDENCE_WORDS)}",
        },
        indent=SCHEMA_INDENT,
    )
