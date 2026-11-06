"""The approval badge the Overview table and the finding cards show for a flagged finding.

No approval recorded is the "needs approval" alarm; a recorded approval shows its decision,
"approved" or "overridden". One place so the cell and the card cannot drift.
"""

from organisation.approval import Approval, ApprovalOutcome, Decision
from report.approval_needed import NEEDS_APPROVAL

# The word and tone a recorded decision shows on a flagged finding.
DECISION_BADGES: dict[Decision, tuple[str, str]] = {
    Decision.APPROVED: ("approved", "ok"),
    Decision.OVERRIDDEN: ("overridden", "warn"),
}
# What a flagged finding shows when the audit records no approval at all.
UNAPPROVED_BADGE: tuple[str, str] = (NEEDS_APPROVAL, "alarm")


def approval_status(approval: ApprovalOutcome) -> tuple[str, str]:
    """Give the word and badge tone a flagged finding shows for this audit's approval decision."""
    if not isinstance(approval, Approval):
        return UNAPPROVED_BADGE
    return DECISION_BADGES[approval.decision]
