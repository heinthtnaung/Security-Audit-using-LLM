"""Which findings need approval, decided by `organisation.approval_rule` from the record.

Pairs each finding with its weighed risk score, so every rendering marks the same findings.
"""

from findings.finding import Finding
from organisation.approval_rule import ApprovalReason, approval_reasons
from report.record import Report

# The mark itself, in every rendering.
NEEDS_APPROVAL = "needs approval"


def reasons_for(report: Report, finding: Finding) -> tuple[ApprovalReason, ...]:
    """Give the reasons one finding in this record needs approval; none if it needs none."""
    return approval_reasons(finding, report.risk.get(finding.advisory.advisory_id))


def needing_approval(report: Report) -> tuple[Finding, ...]:
    """Give the findings this record marks as needing approval, in the record's own order."""
    return tuple(one for one in report.findings if reasons_for(report, one))
