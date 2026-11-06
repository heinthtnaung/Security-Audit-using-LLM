"""Weighing every finding against this environment, when an operator supplied answers.

Without answers there is no Organisation Risk Score and the report says so. Each
finding is scored once per published source, since choosing one would be a precedence
the design leaves open; a council's reading is never an input here.
"""

from pathlib import Path
from typing import Iterable

from findings.finding import Finding
from organisation.answers import OrganisationAnswers, approval_block, read_answers
from organisation.approval import Approval, ApprovalOutcome, NotApproved, read_decision
from organisation.risk import FindingRisk, assess, per_source

NO_ANSWER_FILE = "no answer file was given, so nobody was asked about this environment"


def weigh_findings(
    findings: Iterable[Finding], answers: OrganisationAnswers
) -> tuple[FindingRisk, ...]:
    """Score every finding, once per published source, against the answers that apply to it."""
    return tuple(
        assess(finding, answers.applying_to(finding.advisory.advisory_id), per_source(finding))
        for finding in findings
    )


def read_approval(path: Path) -> ApprovalOutcome:
    """Read the approval an answer file carries, which is usually none."""
    block = approval_block(path)
    if not block:
        return NotApproved("the answer file carries no approval")
    return Approval(
        approver=str(block.get("approver") or ""),
        decision=read_decision(block.get("decision") or ""),
        recorded_at=str(block.get("recorded_at") or ""),
        note=str(block.get("note") or ""),
    )


def organisation_of(path: Path | None) -> tuple[OrganisationAnswers, ApprovalOutcome]:
    """Read what the organisation said, or record that it said nothing."""
    if path is None:
        return OrganisationAnswers(), NotApproved(NO_ANSWER_FILE)
    return read_answers(path), read_approval(path)
