"""The sentences both council renderings share, in one place so the two cannot drift.

Each function gives a phrase or list of phrases; the caller adds the spacing and markup.
Verified (quotation found in the advisory) is a different claim from quoted, so the wording
says which.
"""

from cvss.metrics import METRIC_ORDER
from report.council_record import (
    CouncilAssessment,
    CouncilWithoutVector,
    MemberIdentity,
    MemberSaid,
    MetricRuling,
    Outcome,
    ReadingOrder,
    SaidKind,
)
from report.model_identity import (
    ESCALATION_ROLE,
    ModelDigest,
    ModelIdentity,
    OllamaVersion,
    ServerVersion,
)
from report.provenance import LocalModels

SETTLED = "settled"
NO_VECTOR = "no vector"
SINGLE_ASSESSOR = "single assessor, nothing cross-checked"
# More than one member reached, but every settled metric rests on one member's quotation.
ONE_QUOTATION_EACH = "every metric on one member's quotation, nothing cross-checked"
NOT_ASKED = "not asked"
VERIFIED = "quotation found in the advisory"
UNVERIFIED = "quotation not found in the advisory"
ESCALATED_TO = "→ escalated to"
NO_SETTLEMENT = "no settlement"
NOT_CONTESTED = "is not one of the contested values"
ESCALATION_MODEL = "escalation model"
NO_ESCALATION = "no escalation model named: a metric the council left open stays open"
# Enough of a digest to tell two weights apart on the page; the record keeps it whole.
SHORT_DIGEST = 12
UNKNOWN_DIGEST = "digest unknown"
UNKNOWN_VERSION = "Ollama version unknown"
NOT_THIS_MACHINE = "not this machine"
SAME_EVIDENCE = (
    "same evidence, different reading: members quoted the same words and read different values"
)
READ_IN = {
    ReadingOrder.IN_ORDER: "with the options in order",
    ReadingOrder.REVERSED: "with the options reversed",
}


def who(member: MemberIdentity) -> str:
    """Name a member, adding its family only when it differs from the name."""
    if member.family == member.name:
        return member.name
    return f"{member.name} ({member.family})"


def uncross_checked(outcome: CouncilAssessment | CouncilWithoutVector) -> list[str]:
    """Mark a result that was not cross-checked, saying which way."""
    if outcome.single_assessor:
        return [SINGLE_ASSESSOR]
    if isinstance(outcome, CouncilAssessment) and outcome.nothing_cross_checked:
        return [ONE_QUOTATION_EACH]
    return []


def checked(verified: bool) -> str:
    """Say whether a member's quotation was found in the advisory."""
    return VERIFIED if verified else UNVERIFIED


def unanswered(said: MemberSaid) -> str:
    """Say what a member that did not answer left behind, if it left anything."""
    if said.kind is SaidKind.GUESSED:
        return f"guessed {said.value} with nothing quoted"
    if said.kind is SaidKind.ORDER_SENSITIVE:
        in_order, reversed_order = said.order_values
        return f"order-sensitive: {in_order} with the options in order, {reversed_order} reversed"
    if said.reason:
        return f"{said.kind.value}: {said.reason}"
    return said.kind.value


def declined_one_way(said: MemberSaid) -> list[str]:
    """Name the order a member declined in where the other order did not."""
    ways = [(said.declined_in, SaidKind.DECLINED.value), (said.unverified_in, UNVERIFIED)]
    return [f"{READ_IN[orders[0]]}: {what}" for orders, what in ways if len(orders) == 1]


def same_evidence_said(ruling: MetricRuling) -> list[str]:
    """Flag a metric members read different values from the same verified words, if they did."""
    return [SAME_EVIDENCE] if ruling.same_evidence_different_reading else []


def escalation_named(local: LocalModels | None) -> list[str]:
    """Say which model the metrics the council left open went to, or that none was named."""
    # Nothing where the record does not say how the models were asked.
    if local is None:
        return []
    if local.escalation_model is None:
        return [NO_ESCALATION]
    return [f"{ESCALATION_MODEL} {local.escalation_model}: asked each metric the council left open"]


def models_named(local: LocalModels | None) -> list[str]:
    """Name every model the run asks with the start of its digest, the server's version and host."""
    if local is None:
        return []
    named = ", ".join(model_said(one) for one in local.models)
    # This machine goes unsaid.
    where = f" on {local.remote_host}, {NOT_THIS_MACHINE}" if local.remote_host else ""
    return [f"models: {named}; {version_said(local.ollama_version)}{where}"]


def model_said(model: ModelIdentity) -> str:
    """Name one model, its role where it is not a member, and the start of its digest."""
    role = f" ({model.role})" if model.role == ESCALATION_ROLE else ""
    weights = model.digest[:SHORT_DIGEST] if isinstance(model, ModelDigest) else UNKNOWN_DIGEST
    return f"{model.model}{role} {weights}"


def version_said(version: ServerVersion) -> str:
    """Name the server's version, or say it is unknown; the record says why."""
    return f"Ollama {version.version}" if isinstance(version, OllamaVersion) else UNKNOWN_VERSION


def outcome_said(ruling: MetricRuling) -> str:
    """Say what came of a metric: its outcome, or what escalating it made of the council's."""
    if ruling.escalation is None:
        return ruling.outcome.value
    escalation = ruling.escalation
    sent = f"{escalation.prior.value} {ESCALATED_TO} {escalation.said.member.model}"
    if ruling.outcome is Outcome.SETTLED:
        return f"{sent}: {ruling.value} (verified)"
    return f"{sent}: {NO_SETTLEMENT}, {why_unsettled(escalation.said)}"


def why_unsettled(said: MemberSaid) -> str:
    """Say why what the escalation model said settled nothing."""
    if said.kind is not SaidKind.ANSWERED:
        return unanswered(said)
    if not said.verified:
        return f"{said.value}, {UNVERIFIED}"
    # Verified and the same both ways settles an unresolved metric, so this is a contest.
    return f"{said.value} {NOT_CONTESTED}"


def escalated_who(member: MemberIdentity) -> str:
    """Name the escalation model where it is listed below the council's members."""
    return f"{who(member)}, {ESCALATION_MODEL}"


def chairman_said(ruling: MetricRuling) -> list[str]:
    """Give what the chairman decided and why."""
    said = [
        f"chairman: {ruling.value}" if ruling.value else "",
        ruling.basis,
        confident(ruling.confidence) if ruling.confidence else "",
        f"fell back to {ruling.fallback_source}" if ruling.fallback_source else "",
    ]
    return [one for one in said if one]


def counted(count: int, noun: str) -> str:
    """Give a count with its noun, singular when there is one of them."""
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


def confident(level: str) -> str:
    """Say how confident a member or the chairman was."""
    return f"{level} confidence"


def metrics_settled(count: int) -> str:
    """Count the metrics the chairman settled."""
    return f"{counted(count, 'metric')} {SETTLED}"


def could_not_settle(outcome: CouncilWithoutVector) -> str:
    """Name the metrics a council left open, in specification order."""
    still_open = {*outcome.unresolved_metrics, *outcome.contested_metrics}
    return "could not settle " + ", ".join(one for one in METRIC_ORDER if one in still_open)
