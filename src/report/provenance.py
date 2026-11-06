"""What produced a run, and whether there was a database there to produce it from.

A missing database build date is its own type: Trivy with no database finds nothing and
exits 0, so "unknown" is the difference between a clean repository and a meaningless report.
Fields are read from the tools, not configured, so a run stays checkable.
"""

from dataclasses import dataclass

from report.model_identity import ModelIdentity, ServerVersion
from scoring.version import SCORING_RULES_VERSION

# How both pages name the version, so the two cannot drift.
SCORING_RULES_LABEL = "scoring rules"


@dataclass(frozen=True)
class AdvisoryDatabase:
    """The advisory database this scan joined against, by its own build date."""

    built_at: str

    def __post_init__(self) -> None:
        """Refuse a database with no build date."""
        if not self.built_at.strip():
            raise ValueError("An advisory database must give the date it was built")


@dataclass(frozen=True)
class UnknownAdvisoryDatabase:
    """No build date could be read, so nothing says this scan saw a database at all."""

    reason: str

    def __post_init__(self) -> None:
        """Refuse a missing database date with no reason."""
        if not self.reason:
            raise ValueError("A missing database date must say why it is missing")


Database = AdvisoryDatabase | UnknownAdvisoryDatabase


@dataclass(frozen=True)
class LocalModels:
    """How every local member of the run was asked: server, window, timeout, pinning and orders.

    `order_check` says each metric was asked both orders, counting only where both agreed.
    `escalation_model` is None where none was named. `ollama_version` and `models` say which
    server and weights answered. `remote_host` names another machine, empty where it is this one.
    """

    server: str
    context_tokens: int
    timeout_seconds: float
    temperature: float
    seed: int
    think: bool
    order_check: bool
    escalation_model: str | None
    ollama_version: ServerVersion
    models: tuple[ModelIdentity, ...]
    remote_host: str = ""

    def __post_init__(self) -> None:
        """Refuse a council run that asked no model."""
        if not self.models:
            raise ValueError("A council run asks at least one model; models cannot be empty")


@dataclass(frozen=True)
class RunProvenance:
    """What produced this report, so a reader can judge whether to believe it.

    `local_models` is None only for a run that named no council member. `answers_source` is
    empty for a file run or no answers, and otherwise names how typed answers arrived.
    """

    repository: str
    syft_version: str
    trivy_version: str
    database: Database
    local_models: LocalModels | None = None
    scoring_rules_version: str = SCORING_RULES_VERSION
    answers_source: str = ""

    def __post_init__(self) -> None:
        """Refuse provenance a reader could not reproduce the run from."""
        missing = [
            name
            for name in ("repository", "syft_version", "trivy_version", "scoring_rules_version")
            if not getattr(self, name)
        ]
        if missing:
            raise ValueError(f"A run's provenance needs {', '.join(missing)}")
        if not isinstance(self.database, (AdvisoryDatabase, UnknownAdvisoryDatabase)):
            raise TypeError(f"A run needs a database, not {type(self.database).__name__}")
