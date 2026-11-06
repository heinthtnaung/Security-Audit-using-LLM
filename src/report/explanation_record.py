"""Why a finding's sources differ, as a model wrote it, projected from `council.explanation`.

The `why` is the model's own prose and nothing checked it; only the quotation beside it is
held to the advisory, and only items whose quotation was found there are kept. Dropped items
are recorded too, each with its reason. No score or ruling is computed from any of it.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ExplainedMetric:
    """One disputed metric the model spoke to: its prose, and the quotation in the advisory."""

    metric: str
    why: str
    evidence: str
    evidence_verified: bool


@dataclass(frozen=True)
class DroppedMetric:
    """An item the model offered and nothing kept: what it said, and why it was dropped.

    `evidence_verified` is the quotation check's own answer; a repeat can quote the advisory.
    """

    metric: str
    why: str
    evidence: str
    evidence_verified: bool
    reason: str


@dataclass(frozen=True)
class SourcesExplained:
    """A model's account of why one finding's sources differ, kept item by item.

    `dropped_items` are the items not kept, each with its reason.
    """

    advisory_id: str
    model: str
    prompt_version: str
    items: tuple[ExplainedMetric, ...]
    dropped_items: tuple[DroppedMetric, ...] = ()

    @property
    def dropped(self) -> int:
        """Count the items not kept."""
        return len(self.dropped_items)

    def __post_init__(self) -> None:
        """Refuse an explanation with no item kept."""
        if not self.items:
            raise ValueError(f"{self.advisory_id} kept no item, so it was not explained")


@dataclass(frozen=True)
class SourcesNotExplained:
    """A finding with no explanation of its sources, why there is none, and what was not kept.

    `model` and `prompt_version` name the explainer where one was asked, empty where none was.
    """

    advisory_id: str
    because: str
    dropped_items: tuple[DroppedMetric, ...] = ()
    model: str = ""
    prompt_version: str = ""

    @property
    def asked(self) -> bool:
        """Say whether a model was asked, and so whether the record names one."""
        return bool(self.model)

    def __post_init__(self) -> None:
        """Refuse an unexplained absence, or model output that does not name what produced it."""
        if not self.because:
            raise ValueError(f"{self.advisory_id} has no explanation and no reason why")
        if bool(self.model) != bool(self.prompt_version):
            raise ValueError(f"{self.advisory_id} names a model or a prompt version, not both")
        if self.dropped_items and not self.asked:
            raise ValueError(f"{self.advisory_id} holds dropped items and names no model")


ExplanationRecord = SourcesExplained | SourcesNotExplained
