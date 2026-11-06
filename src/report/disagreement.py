"""How far apart a finding's sources are: where they disagree, and how much it would change.

Disagreement is measured on the metrics, not the scores -- two sources can reach one score
from different vectors. A spread that crosses a severity band sorts above a wider spread
inside one band, because crossing a band moves the response time.
"""

from cvss.score import SEVERITY_BAND_NAMES, severity_band
from findings.finding import Finding

# Worst first; the band names come from `cvss.score`.
BAND_ORDER: tuple[str, ...] = SEVERITY_BAND_NAMES

SCORE_DECIMALS = 1


def sources_disagree(finding: Finding) -> bool:
    """Say whether the readable sources differ on any metric, whatever their scores came to."""
    return bool(finding.disputed_metrics())


def carries_a_refused_source(finding: Finding) -> bool:
    """Say whether any source's vector was refused, which leaves its reading unknown."""
    return bool(finding.unreadable)


def sources_agree(finding: Finding) -> bool:
    """Say whether every source was read and the readings match on every metric."""
    # A refused vector cannot be read, so a finding carrying one never counts as agreeing.
    return finding.is_scored and not finding.unreadable and not sources_disagree(finding)


def agreement_unchecked(finding: Finding) -> bool:
    """Say whether the readable sources match beside a source whose vector was refused."""
    return finding.is_scored and bool(finding.unreadable) and not sources_disagree(finding)


def score_spread(finding: Finding) -> float:
    """Give the distance between the highest and lowest score published for a finding."""
    scores = [score.base_score for score in finding.scores]
    if len(scores) < 2:
        return 0.0
    return round(max(scores) - min(scores), SCORE_DECIMALS)


def bands_crossed(finding: Finding) -> tuple[str, ...]:
    """Name the distinct severity bands a finding's sources put it in, worst first."""
    reached = {severity_band(score.base_score) for score in finding.scores}
    return tuple(name for name in BAND_ORDER if name in reached)


def crosses_a_band(finding: Finding) -> bool:
    """Say whether the sources disagree about the response this finding deserves."""
    return len(bands_crossed(finding)) > 1


def most_contested_first(findings: tuple[Finding, ...]) -> tuple[Finding, ...]:
    """Order findings by how much their disagreement could change a decision."""
    return tuple(sorted(findings, key=contest_order))


def contest_order(finding: Finding) -> tuple[int, float, int, str, str]:
    """Rank a finding by consequence, then by name so two runs order identically."""
    # Negated so the tie-breaks stay ascending and the order is stable.
    return (
        -len(bands_crossed(finding)),
        -score_spread(finding),
        -len(finding.disputed_metrics()),
        finding.advisory.advisory_id,
        finding.component.name,
    )
