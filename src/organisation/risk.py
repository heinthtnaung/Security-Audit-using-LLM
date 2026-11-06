"""What this environment's answers make of one finding, once for every source.

Choosing one source would be a precedence the design leaves open, so a finding
with two published vectors gets two organisation scores; what matters is whether
they land in different bands. Only published sources are weighed, never a
council's reading. A finding nobody scored still gets one provisional score.
"""

from dataclasses import dataclass

from findings.finding import Finding
from scoring.bands import RISK_BANDS
from scoring.category import CategoryScore, score_category
from scoring.library import ANSWERED_CATEGORIES, answers_for, refuse_incomplete
from scoring.question import Answer, Category
from scoring.risk_score import RiskScore, organisation_risk_score
from scoring.technical import TechnicalInput, UnknownTechnicalSeverity, from_cvss_base_score

BAND_ORDER: tuple[str, ...] = tuple(name for _, name in RISK_BANDS)

NOTHING_PUBLISHED = "no source published a readable v3 vector"


@dataclass(frozen=True)
class FindingRisk:
    """Every organisation score one finding carries, one per technical severity offered."""

    advisory_id: str
    scores: tuple[RiskScore, ...]

    @property
    def bands(self) -> tuple[str, ...]:
        """Name the distinct bands this finding lands in, worst first."""
        reached = {one.band for one in self.scores}
        return tuple(name for name in BAND_ORDER if name in reached)

    @property
    def band_depends_on_the_source(self) -> bool:
        """Say whether which source you believe changes what this organisation should do."""
        return len(self.bands) > 1

    @property
    def is_provisional(self) -> bool:
        """Say whether anything here was answered Unknown, or nobody scored the finding."""
        return any(one.is_provisional for one in self.scores)


def assess(
    finding: Finding, answers_by_id: dict[str, Answer], technical: tuple[TechnicalInput, ...]
) -> FindingRisk:
    """Score one finding once for each technical severity it was offered."""
    if not technical:
        raise ValueError(f"{finding.advisory.advisory_id} was offered no technical severity")
    # Held here, not only where a file is read, so no caller can score an incomplete set.
    refuse_incomplete(answers_by_id)
    categories = category_scores(answers_by_id)
    return FindingRisk(
        advisory_id=finding.advisory.advisory_id,
        scores=tuple(weigh(one, categories) for one in technical),
    )


def weigh(technical: TechnicalInput, categories: dict[Category, CategoryScore]) -> RiskScore:
    """Put one technical severity through the engine with this environment's categories."""
    return organisation_risk_score(
        technical=technical,
        exposure=categories[Category.EXPOSURE],
        business=categories[Category.BUSINESS],
        threat=categories[Category.THREAT],
    )


def category_scores(answers_by_id: dict[str, Answer]) -> dict[Category, CategoryScore]:
    """Score every category an organisation is asked about, from answers given by id."""
    return {
        category: score_category(category, answers_for(category, answers_by_id))
        for category in ANSWERED_CATEGORIES
    }


def per_source(finding: Finding) -> tuple[TechnicalInput, ...]:
    """Give one technical severity per source that scored the finding, each naming its source."""
    if not finding.scores:
        return (UnknownTechnicalSeverity(reason=NOTHING_PUBLISHED),)
    return tuple(from_cvss_base_score(one.base_score, one.source) for one in finding.scores)
