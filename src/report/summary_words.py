"""The summary line both renderings lead with: its counts, and what they leave out.

In one place so the two pages cannot drift. A refused source is counted, but not as a
disagreement. "0 findings" over unread manifests, or an empty inventory, gets a pointer to what
was left out. Findings needing approval are counted beside the rule, and secrets at none too.
"""

from organisation.approval import NotApproved
from organisation.approval_rule import ApprovalReason
from report.approval_needed import needing_approval
from report.council_words import counted
from report.disagreement import carries_a_refused_source, sources_disagree
from report.record import Report

DISAGREE_CLAUSE = "{} sources that disagree"
REFUSED_CLAUSE = "{} a source this calculator could not read"
UNREAD_POINTER = "Not in these counts: {} with no lock file Syft reads, named under not assessed."
EMPTY_POINTER = "Not a clean result: Syft catalogued no component, so nothing was checked."
APPROVAL_COUNT = "Approval is needed for {} of {}: {}."
BOTH_HALVES = f"{ApprovalReason.RISK_BAND.value}, or {ApprovalReason.SOURCES_DISAGREE.value}"
UNWEIGHED = (
    f"With no organisation answers, no finding was checked for {ApprovalReason.RISK_BAND.value}."
)
UNAPPROVED = "No approval is recorded for this audit."
# No apostrophe: the page escapes one to `&#x27;`, a number to anything reading its figures.
SECRETS_COUNT = "{} matched the secret rules built into Trivy."


def counts(report: Report) -> str:
    """Count the findings, those whose readable sources disagree, and any with a refused source."""
    # A vector the calculator refused is not counted as a dissent, whatever it says.
    contested = len([one for one in report.findings if sources_disagree(one)])
    refused = len([one for one in report.findings if carries_a_refused_source(one)])
    found = counted(len(report.findings), "finding")
    catalogued = counted(report.component_count, "component")
    said = f"{found} across {catalogued}. {DISAGREE_CLAUSE.format(carry(contested))}"
    # Omitted at none, so a run with no refused source reads as before.
    return f"{said}; {REFUSED_CLAUSE.format(carry(refused))}." if refused else f"{said}."


def carry(count: int) -> str:
    """Give a count of findings with its verb, singular when there is one of them."""
    return f"{count} carries" if count == 1 else f"{count} carry"


def unread_pointer(report: Report) -> str:
    """Point from the counts to the manifests nothing was read from, or give nothing when none."""
    unread = report.coverage.unread_manifests
    if not unread:
        return ""
    return UNREAD_POINTER.format(counted(len(unread), "manifest"))


def inventory_pointer(report: Report) -> str:
    """Say an inventory of nothing is not a clean result, or give nothing when it holds one."""
    if report.component_count:
        return ""
    return EMPTY_POINTER


def approval_count(report: Report) -> str:
    """Count the findings needing approval and the rule that marked them, and say if unapproved."""
    if not report.findings:
        return ""
    needing = len(needing_approval(report))
    # Without answers there is no risk score, so only disagreement could mark a finding.
    halves = BOTH_HALVES if report.risk else ApprovalReason.SOURCES_DISAGREE.value
    said = [APPROVAL_COUNT.format(needing, len(report.findings), halves)]
    if not report.risk:
        said.append(UNWEIGHED)
    if needing and isinstance(report.approval, NotApproved):
        said.append(UNAPPROVED)
    return " ".join(said)


def secrets_count(report: Report) -> str:
    """Count the secrets Trivy's built-in rules matched, and say so at none too."""
    return SECRETS_COUNT.format(counted(len(report.secrets), "secret"))
