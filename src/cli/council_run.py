"""Putting the council to the findings that need one, when the operator named members.

Scoped to findings whose published sources do not settle them: a measured
two-member run over 18 findings dropped from 288 calls to 80 that way.
`--council-all-findings` asks about every one, the only way to catch two sources
that agree and are both wrong. A finding nobody scored, or one carrying a source
that could not be read, is asked about too. Every skip is recorded with its reason.

No fallback source is chosen here: picking one would be the precedence the design
refuses to set, so every metric gets a `NoFallbackPublished`. Every council is asked
before any escalation, so the escalation calls come last and together; no prompt or
ruling reads the order, so the record is the same byte for byte.
"""

from cli.council_detail import rulings_of
from cli.council_outcome import outcome_of
from cli.progress import NO_PROGRESS, CouncilProgress, orders_asked
from council.escalation import escalate, refuse_unfit_escalation
from council.prompt import build_prompt
from council.providers import ollama_member
from council.roster import Member, Roster, members_to_ask
from council.ruling import NoFallbackPublished
from council.run import CouncilRun
from council.runner import PROVIDER_CLIENTS, assess
from cvss.metrics import METRIC_ORDER
from findings.finding import Finding
from report.council_record import CouncilNotAsked, CouncilOutcome

# Every audit asks each metric in both orders; only the eval harness turns it off.
ORDER_CHECK = True

SOURCES_AGREE = "no published source disagrees, so there is nothing to reconcile"
NO_TEXT_TO_READ = "the advisory carries no text for a member to read"

NO_FALLBACK = NoFallbackPublished(
    reason="no published source may be preferred, so none was offered as a fallback"
)
FALLBACKS = {metric: NO_FALLBACK for metric in METRIC_ORDER}


def build_roster(models: tuple[str, ...]) -> Roster:
    """Turn the models an operator named into a roster of members on the settings' server."""
    return Roster(tuple(ollama_member(model) for model in models))


def escalation_member(model: str | None) -> Member | None:
    """Describe the escalation model as a member on the settings' server, or None where unnamed."""
    if model is None:
        return None
    return ollama_member(model)


def assessments(
    findings: tuple[Finding, ...], roster: Roster,
    clients=PROVIDER_CLIENTS, progress=NO_PROGRESS,
    every_finding: bool = False, order_check: bool = ORDER_CHECK,
    escalation: Member | None = None,
) -> tuple[CouncilOutcome, ...]:
    """Put the council to the findings that need one, and record why the rest were passed over."""
    # Refused before any call, not once the first advisory's council has run.
    refuse_unfit_escalation(escalation, tuple(one.name for one in roster.members), clients)
    # Every council before any escalation, so the escalation calls come last and together.
    asking = to_assess(findings, every_finding)
    try:
        councils = [
            (one, council_on(one, roster, clients, progress, order_check)) for one in asking
        ]
        assessed = [
            escalated_at(position, one, council, escalation, clients, progress)
            for position, (one, council) in enumerate(councils, start=1)
        ]
        return (*assessed, *passed_over(findings, every_finding))
    finally:
        # Close the bar's line even if a call raised, so the next phase does not land on it.
        progress.finish()


def to_assess(findings: tuple[Finding, ...], every_finding: bool) -> tuple[Finding, ...]:
    """Give the findings this run will actually put to the council."""
    return tuple(one for one in findings if not skipped_because(one, every_finding))


def passed_over(findings: tuple[Finding, ...], every_finding: bool) -> tuple[CouncilNotAsked, ...]:
    """Record every finding the council was not put to, each with the reason it was not."""
    skipped = [(one, skipped_because(one, every_finding)) for one in findings]
    return tuple(
        CouncilNotAsked(one.advisory.advisory_id, because) for one, because in skipped if because
    )


def skipped_because(finding: Finding, every_finding: bool) -> str:
    """Say why a finding is not put to the council, or nothing at all where it is."""
    if not advisory_text(finding):
        return NO_TEXT_TO_READ
    # Nobody published a vector, so there is no agreement and the council is the only severity.
    if every_finding or not finding.is_scored:
        return ""
    # An unreadable source is unchecked, not agreement: it may disagree with every read one.
    if finding.unreadable or finding.disputed_metrics():
        return ""
    return SOURCES_AGREE


def assess_one(
    finding: Finding, roster: Roster, clients,
    progress=NO_PROGRESS, order_check: bool = ORDER_CHECK,
    escalation: Member | None = None,
) -> CouncilOutcome:
    """Put one advisory to the council and escalate what it left open, handing on any vector."""
    council = council_on(finding, roster, clients, progress, order_check)
    return escalated_outcome(finding, council, escalation, clients, progress)


def council_on(
    finding: Finding, roster: Roster, clients, progress, order_check: bool
) -> CouncilRun:
    """Put one advisory to every member of the council, escalating nothing yet."""
    progress.starting(finding.advisory.advisory_id)
    return assess(advisory_text(finding), roster, FALLBACKS, clients, progress.asking, order_check)


def escalated_at(
    position: int, finding: Finding, council: CouncilRun,
    escalation: Member | None, clients, progress,
) -> CouncilOutcome:
    """Go back to the advisory at this place in the run and escalate what its council left open."""
    progress.returning_to(position, finding.advisory.advisory_id)
    return escalated_outcome(finding, council, escalation, clients, progress)


def escalated_outcome(
    finding: Finding, council: CouncilRun, escalation: Member | None, clients, progress
) -> CouncilOutcome:
    """Escalate what one advisory's council left open, and record what the run came to."""
    text = advisory_text(finding)
    run = escalate(council, text, escalation, clients, progress.escalating)
    # The text the members read, which their quotations are re-checked against.
    rulings = rulings_of(run, build_prompt(METRIC_ORDER[0], text).advisory_shown)
    return outcome_of(finding, run, rulings)


def watching(
    findings: tuple[Finding, ...], roster: Roster, out,
    every_finding: bool = False, order_check: bool = ORDER_CHECK, debug: bool = False,
) -> CouncilProgress:
    """Count the calls this roster will make over the findings it will be asked about."""
    # Count only the findings and members this run will ask, or the bar never fills.
    asking = to_assess(findings, every_finding)
    orders = orders_asked(order_check)
    return CouncilProgress(len(asking), len(members_to_ask(roster)), out, orders, debug)


def advisory_text(finding: Finding) -> str:
    """Give the text a member reads, which is the advisory's own description."""
    return finding.advisory.details.strip()
