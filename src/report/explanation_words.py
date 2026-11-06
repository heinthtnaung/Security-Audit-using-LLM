"""The sentences both explanation renderings share, in one place so the two cannot drift.

The model's prose is labelled as the model's on every item, since nothing checked it.
"""

from report.council_words import VERIFIED, counted
from report.explanation_record import SourcesExplained, SourcesNotExplained

HEADING = "Why the sources differ"
LEDE = (
    "Written by a model from the advisory text, for each metric the published sources read "
    "differently. Only each quotation is checked: an item is kept where its quotation is in the "
    "advisory, one per disputed metric. The explanation beside it is the model's own words, and "
    "no score or ruling is computed from it."
)
MODEL_WRITTEN = "model-written, not checked"
EXPLAINED_BY = "explained by"
NOT_EXPLAINED = "not explained"
DROPPED = "not kept"
# Every item kept carries a quotation found in the advisory; nothing else is kept.
CHECKED = VERIFIED


def explained_by(record: SourcesExplained) -> list[str]:
    """Say which model explained a finding, and how many of its items were not kept."""
    named = [f"{EXPLAINED_BY} {record.model}"]
    if not record.dropped:
        return named
    return [*named, f"{counted(record.dropped, 'item')} {DROPPED}"]


def not_explained(record: SourcesNotExplained) -> str:
    """Say that a finding was not explained, and why."""
    return f"{NOT_EXPLAINED}: {record.because}"


def sources_on(finding, metric: str) -> list[str]:
    """Give what each readable source published for one metric, in source-name order."""
    return [f"{score.source} {score.parsed_vector.metrics[metric]}" for score in finding.scores]
