"""The report record: everything the run computed, built once and rendered as text, JSON and HTML.

Every score keeps the vector it came from, so the figures re-derive by hand. What was not
assessed is a field, not an omission; see `report.absences`.
"""

from dataclasses import dataclass, field
from typing import Iterable, Mapping

from deps.syft_report import Catalogue, UnidentifiedArtifact
from deps.trivy_report import Advisory
from deps.trivy_secrets import SecretFinding
from findings.finding import Finding, unmatched_purls
from organisation.approval import ApprovalOutcome, NotApproved
from organisation.risk import FindingRisk
from report.absences import NO_APPROVAL_GIVEN, Absence, Coverage, absences
from report.council_record import CouncilOutcome
from report.explanation_record import ExplanationRecord
from report.provenance import RunProvenance


@dataclass(frozen=True)
class Report:
    """One audit: what was found, what matched nothing, and what was not assessed."""

    provenance: RunProvenance
    findings: tuple[Finding, ...]
    component_count: int
    # A component nothing matched may be clean; an advisory matching no component
    # is a CVE that fell out of the join, which looks clean and is not.
    components_without_findings: tuple[str, ...]
    advisories_without_components: tuple[str, ...]
    # Answer overrides naming an advisory this scan did not find. Counted, not
    # refused: a file reused across repos names advisories absent from one.
    overrides_without_findings: tuple[str, ...]
    # Catalogued but joinable to no advisory, so never a finding. Counted so a
    # dropped entry cannot silently lose a CVE.
    unidentified_artifacts: tuple[UnidentifiedArtifact, ...]
    not_assessed: tuple[Absence, ...]
    council: Mapping[str, CouncilOutcome] = field(default_factory=dict)
    # Why the sources differ, as a model wrote it. Nothing is computed from it.
    explanations: Mapping[str, ExplanationRecord] = field(default_factory=dict)
    risk: Mapping[str, FindingRisk] = field(default_factory=dict)
    approval: ApprovalOutcome = field(default_factory=lambda: NotApproved(NO_APPROVAL_GIVEN))
    coverage: Coverage = Coverage()
    # Where a secret-scanning rule matched. No CVSS, so never a finding, and
    # never the secret itself.
    secrets: tuple[SecretFinding, ...] = ()


def build_report(
    provenance: RunProvenance, catalogue: Catalogue,
    findings: Iterable[Finding], advisories_by_purl: Mapping[str, tuple[Advisory, ...]],
    council: Iterable[CouncilOutcome] = (), risk: Iterable[FindingRisk] = (),
    approval: ApprovalOutcome | None = None, overridden: Iterable[str] = (),
    coverage: Coverage = Coverage(), explanations: Iterable[ExplanationRecord] = (),
    secrets: Iterable[SecretFinding] = (),
) -> Report:
    """Gather one run into the record both renderings read."""
    raised, decided = tuple(findings), approval or NotApproved(NO_APPROVAL_GIVEN)
    settled, weighed, explained = by_advisory(council), by_advisory(risk), by_advisory(explanations)
    return Report(
        provenance=provenance,
        findings=raised,
        component_count=len(catalogue.components),
        components_without_findings=purls_without_findings(catalogue, raised),
        advisories_without_components=unmatched_purls(catalogue.components, advisories_by_purl),
        unidentified_artifacts=catalogue.unidentified,
        overrides_without_findings=overrides_without_findings(overridden, raised),
        not_assessed=absences(
            settled, weighed, decided, coverage, len(catalogue.components), explained, raised
        ),
        council=settled,
        explanations=explained,
        risk=weighed,
        approval=decided,
        coverage=coverage,
        secrets=tuple(secrets),
    )


def by_advisory(entries: Iterable) -> dict:
    """Index anything carrying an advisory id by the advisory it is about."""
    return {one.advisory_id: one for one in entries}


def purls_without_findings(catalogue: Catalogue, findings: tuple[Finding, ...]) -> tuple[str, ...]:
    """Name the installed components nothing was published against."""
    affected = {finding.component.purl for finding in findings}
    return tuple(sorted(one.purl for one in catalogue.components if one.purl not in affected))


def overrides_without_findings(
    overridden: Iterable[str], findings: tuple[Finding, ...]
) -> tuple[str, ...]:
    """Name the answer overrides that matched nothing this scan found."""
    found = {finding.advisory.advisory_id for finding in findings}
    return tuple(sorted(one for one in overridden if one not in found))
