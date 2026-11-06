"""Which findings need a human's approval: one deterministic rule.

A High or Critical Organisation Risk Score needs a human, and a High from any
source counts. Published sources that disagree need one too, since nothing here
resolves a conflict. Without answers there is no risk score, so only the second
half can mark a finding.
"""

from enum import Enum

from findings.finding import Finding
from organisation.risk import FindingRisk

# The organisation bands that need a human.
APPROVAL_BANDS = ("Critical", "High")


class ApprovalReason(Enum):
    """Why a finding needs approval, in the words every rendering gives it."""

    RISK_BAND = "a High or Critical Organisation Risk Score"
    SOURCES_DISAGREE = "sources that disagree"


def approval_reasons(
    finding: Finding, weighed: FindingRisk | None
) -> tuple[ApprovalReason, ...]:
    """Name each half of the rule a finding meets, in the rule's order; none if it needs none."""
    refuse_another_findings_risk(finding, weighed)
    reasons = []
    if weighed is not None and any(band in APPROVAL_BANDS for band in weighed.bands):
        reasons.append(ApprovalReason.RISK_BAND)
    if finding.disputed_metrics():
        reasons.append(ApprovalReason.SOURCES_DISAGREE)
    return tuple(reasons)


def refuse_another_findings_risk(finding: Finding, weighed: FindingRisk | None) -> None:
    """Refuse a risk score weighed for some other advisory, which would mark the wrong finding."""
    if weighed is None or weighed.advisory_id == finding.advisory.advisory_id:
        return
    raise ValueError(
        f"The risk for {weighed.advisory_id} was paired with {finding.advisory.advisory_id}"
    )
