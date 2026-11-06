"""Read what a member said into an answer, a guess or an absence, or refuse it loudly.

Models put prose around their JSON, stop mid-object, answer the wrong metric and
invent fields; none of that may become an answer. Only what cannot change meaning
is tolerated: prose around the object, case, and a value written as its whole pair
(`AV:N`). The three things a member can do are three types: an absence
(`NO_EVIDENCE`), a value with no quotation (a guess), or a value with one (an
answer). An illegal value is refused, never repaired.
"""

from typing import Any, Mapping

from council.answer import (
    Confidence,
    MemberAnswer,
    MemberFoundNoEvidence,
    MemberGuessed,
    MemberIdentity,
    MemberReply,
)
from council.reply_format import (
    CONFIDENCE_BY_WORD,
    CONFIDENCE_FIELD,
    CONFIDENCE_WORDS,
    EVIDENCE_FIELD,
    METRIC_FIELD,
    NO_EVIDENCE_VALUE,
    REQUIRED_FIELDS,
    VALUE_FIELD,
)
from council.reply_object import MalformedReply, excerpt, extract_object

PAIR_SEPARATOR = ":"


def read_reply(text: str, metric: str, member: MemberIdentity) -> MemberReply:
    """Read one member's reply into an answer, a guess at a value, or an absence."""
    fields = extract_object(text)
    refuse_other_metric(fields, metric, text)
    refuse_missing_fields(fields, text, (VALUE_FIELD,))
    value = read_value(fields, metric)
    if value == NO_EVIDENCE_VALUE:
        # A quotation alongside NO_EVIDENCE supports nothing; record only the absence.
        return MemberFoundNoEvidence(metric=metric, member=member)
    if quoted_nothing(fields):
        return build_guess(metric, value, member, text)
    refuse_missing_fields(fields, text, REQUIRED_FIELDS)
    return build_answer(fields, metric, value, member, text)


def quoted_nothing(fields: Mapping[str, Any]) -> bool:
    """Say whether the reply offered a quotation field and left it empty."""
    # A value with an empty quotation is a guess; leaving the field out is malformed.
    quotation = fields.get(EVIDENCE_FIELD)
    return isinstance(quotation, str) and not quotation.strip()


def build_guess(metric: str, value: str, member: MemberIdentity, text: str) -> MemberGuessed:
    """Record a value nothing was quoted for, refusing one the metric does not allow."""
    try:
        return MemberGuessed(metric=metric, value=value, member=member)
    except (TypeError, ValueError) as fault:
        raise MalformedReply(f"{fault} -- {excerpt(text)}") from fault


def build_answer(
    fields: Mapping[str, Any],
    metric: str,
    value: str,
    member: MemberIdentity,
    text: str,
) -> MemberAnswer:
    """Build the answer, turning the contract's own refusals into malformed replies."""
    try:
        return MemberAnswer(
            metric=metric,
            value=value,
            evidence=read_evidence(fields, metric, text),
            confidence=read_confidence(fields, text),
            member=member,
        )
    except (TypeError, ValueError) as fault:
        raise MalformedReply(f"{fault} -- {excerpt(text)}") from fault


def refuse_missing_fields(fields: Mapping[str, Any], text: str, names: tuple[str, ...]) -> None:
    """Refuse a reply that left out a field the prompt asked for."""
    missing = [name for name in names if name not in fields]
    if not missing:
        return
    raise MalformedReply(f"The reply has no {', '.join(missing)} -- {excerpt(text)}")


def refuse_other_metric(fields: Mapping[str, Any], metric: str, text: str) -> None:
    """Refuse a reply that names a metric other than the one it was asked about."""
    answered = fields.get(METRIC_FIELD)
    if answered is None or str(answered).strip().upper() == metric:
        return
    raise MalformedReply(
        f"The reply answers {str(answered)!r}, but {metric} was asked -- {excerpt(text)}"
    )


def read_value(fields: Mapping[str, Any], metric: str) -> str:
    """Read the value, allowing the letter alone or the whole 'AV:N' pair."""
    value = fields[VALUE_FIELD]
    if not isinstance(value, str):
        raise MalformedReply(f"{metric} was answered with {type(value).__name__}, not a value")
    spelled = value.strip().upper()
    if spelled == NO_EVIDENCE_VALUE:
        return NO_EVIDENCE_VALUE
    name, separator, letter = spelled.partition(PAIR_SEPARATOR)
    return letter.strip() if separator and name == metric else spelled


def read_evidence(fields: Mapping[str, Any], metric: str, text: str) -> str:
    """Read the quotation, refusing a reply that put something other than text there."""
    evidence = fields[EVIDENCE_FIELD]
    if isinstance(evidence, str):
        return evidence
    raise MalformedReply(
        f"{metric} was quoted as {type(evidence).__name__}, not text -- {excerpt(text)}"
    )


def read_confidence(fields: Mapping[str, Any], text: str) -> Confidence:
    """Read the confidence word, refusing a level the prompt never offered."""
    said = str(fields[CONFIDENCE_FIELD]).strip().lower()
    level = CONFIDENCE_BY_WORD.get(said)
    if level is None:
        allowed = ", ".join(CONFIDENCE_WORDS)
        raise MalformedReply(
            f"{said!r} is not a confidence; the prompt offers {allowed} -- {excerpt(text)}"
        )
    return level
