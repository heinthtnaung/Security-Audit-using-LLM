"""Read Ollama's reply envelope into the reply text, or a failure that says why.

An envelope carries no answer four ways, each a `ModelUnavailable` the runner
records as a failed member: it is not an object, the server set `error`, the
model was cut off (`done_reason` is `length`), or `response` is empty. Only
`response` is read as the answer; `thinking` never is.
"""

from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from council.transport import ModelUnavailable

MODEL_FIELD = "model"
RESPONSE_FIELD = "response"
ERROR_FIELD = "error"
THINKING_FIELD = "thinking"
DONE_REASON_FIELD = "done_reason"
PROMPT_COUNT_FIELD = "prompt_eval_count"
CUT_OFF = "length"


class Pinned(Protocol):
    """Names the pinned model, so a failure can be said of it."""

    model: str


@dataclass(frozen=True)
class ModelReply:
    """The reply text, and the model the server named (the pinned name if it named none)."""

    text: str
    model: str


def read_envelope(envelope: Any, pinning: Pinned) -> ModelReply:
    """Read Ollama's reply envelope, refusing one that carries no finished answer."""
    if not isinstance(envelope, Mapping):
        raise ModelUnavailable(f"{pinning.model} returned {type(envelope).__name__}, not an object")
    if envelope.get(ERROR_FIELD):
        raise ModelUnavailable(f"{pinning.model} refused the request: {envelope[ERROR_FIELD]}")
    if envelope.get(DONE_REASON_FIELD) == CUT_OFF:
        raise ModelUnavailable(f"{pinning.model} was cut off before it finished: {held(envelope)}")
    text = envelope.get(RESPONSE_FIELD)
    if not isinstance(text, str) or not text.strip():
        raise ModelUnavailable(f"{pinning.model} answered with no text at all: {held(envelope)}")
    return ModelReply(text=text, model=envelope.get(MODEL_FIELD) or pinning.model)


def held(envelope: Mapping[str, Any]) -> str:
    """Say what an unusable envelope held: how much reply, how much thinking, why it stopped."""
    reply = str(envelope.get(RESPONSE_FIELD) or "")
    thinking = str(envelope.get(THINKING_FIELD) or "")
    stopped = envelope.get(DONE_REASON_FIELD)
    return (
        f"{len(reply)} characters of reply and {len(thinking)} of thinking, "
        f"with {DONE_REASON_FIELD} {stopped!r}"
    )
