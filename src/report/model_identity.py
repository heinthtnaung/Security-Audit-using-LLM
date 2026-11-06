"""Which weights answered and which server: each local model's digest, and Ollama's version.

A tag like `gemma4:latest` can be re-pointed, so the digest is what names the weights. Each
is known or not, and a type says which; an unknown digest keeps the reason the server gave.
"""

from dataclasses import dataclass

MEMBER_ROLE = "member"
ESCALATION_ROLE = "escalation"


@dataclass(frozen=True)
class ModelDigest:
    """The digest the server holds for one model the run asks, and what the run asks it as."""

    model: str
    role: str
    digest: str

    def __post_init__(self) -> None:
        """Refuse a digest that names no model or no weights."""
        if not self.model or not self.digest:
            raise ValueError("A model digest must name the model and its digest")


@dataclass(frozen=True)
class UnknownDigest:
    """A model the run asks whose digest the server did not give, and why."""

    model: str
    role: str
    reason: str

    def __post_init__(self) -> None:
        """Refuse an unknown digest that names no model or no reason."""
        if not self.model or not self.reason:
            raise ValueError("An unknown digest must name the model and say why it is unknown")


@dataclass(frozen=True)
class OllamaVersion:
    """The version the local model server reports of itself."""

    version: str

    def __post_init__(self) -> None:
        """Refuse an empty version."""
        if not self.version.strip():
            raise ValueError("An Ollama version must say what it is")


@dataclass(frozen=True)
class UnknownOllamaVersion:
    """No version could be read from the server, and why."""

    reason: str

    def __post_init__(self) -> None:
        """Refuse an unknown version that gives no reason."""
        if not self.reason:
            raise ValueError("An unknown Ollama version must say why it is unknown")


ModelIdentity = ModelDigest | UnknownDigest
ServerVersion = OllamaVersion | UnknownOllamaVersion
