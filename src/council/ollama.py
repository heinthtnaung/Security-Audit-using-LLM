"""The Ollama member: one pinned model, asked one question on the settings' server.

Pinning is what makes a local member reproducible: a fixed model, temperature 0,
a seed, no thinking, and a fixed context window. Temperature, seed and thinking
are constants here, not settings. `build_request` refuses a prompt too long for
the window, and `ask` holds the estimate to the server's own token count, because
Ollama cuts an overlong prompt without saying so. Nothing here parses the reply.
"""

from dataclasses import dataclass, field
from typing import Any

from council.env_file import REMOTE_SERVER
from council.envelope import MODEL_FIELD, PROMPT_COUNT_FIELD, ModelReply, read_envelope
from council.question import Question
from council.settings import LOOPBACK_HOSTS, current_settings, on_this_machine
from council.transport import ModelUnavailable, Transport, post_json

GENERATE_PATH = "/api/generate"

# Constants, not settings: a member that samples or thinks by default is not pinned.
PINNED_TEMPERATURE = 0
PINNED_SEED = 11
# Sent to every model, so no model's own default decides.
PINNED_THINKING = False

# Four characters per token: rough, and every model counts its own way.
CHARACTERS_PER_TOKEN = 4

# Headroom for the rough estimate: better to refuse a prompt that would just fit
# than to send one that gets silently cut.
USABLE_CONTEXT_FRACTION = 0.75

# A prompt counted at less than this fraction of the estimate was cut by the server.
CUT_PROMPT_FRACTION = 0.7

JSON_REPLY_FORMAT = "json"


@dataclass(frozen=True)
class LocalModel:
    """The pinning of one local member: model, seed, context window and host.

    `host` is pinned too: `refuse_remote_host` holds it to loopback or the one
    opted-in server, which is what makes `ran_local` an observation.
    """

    # The operator's setting where none is given (`council.settings`, read once).
    model: str = field(default_factory=lambda: current_settings().model)
    seed: int = PINNED_SEED
    context_tokens: int = field(default_factory=lambda: current_settings().context_tokens)
    host: str = field(default_factory=lambda: current_settings().server)

    def __post_init__(self) -> None:
        """Refuse a pinning that is not one, and a host neither here nor the opted-in server."""
        if not self.model:
            raise ValueError("A local member must name the model it runs")
        if self.context_tokens <= 0:
            raise ValueError(f"{self.model} needs a context length, not {self.context_tokens}")
        refuse_remote_host(self.host)


def ask(
    prompt: Question,
    pinning: LocalModel | None = None,
    transport: Transport = post_json,
) -> ModelReply:
    """Put one question to a local model and give back what it said."""
    pinned = pinning or LocalModel()
    envelope = transport(generate_url(pinned), build_request(prompt, pinned))
    return read_answer(envelope, prompt, pinned)


def read_answer(envelope: Any, prompt: Question, pinning: LocalModel) -> ModelReply:
    """Read the reply to one prompt, refusing it if the server did not read the prompt whole."""
    reply = read_envelope(envelope, pinning)
    refuse_cut_prompt(envelope.get(PROMPT_COUNT_FIELD), prompt, pinning)
    return reply


def generate_url(pinning: LocalModel) -> str:
    """Give the generate endpoint of a pinning's host."""
    return f"{pinning.host.rstrip('/')}{GENERATE_PATH}"


def build_request(prompt: Question, pinning: LocalModel) -> dict[str, Any]:
    """Build the Ollama request for one prompt, pinned, not streamed, and sure to fit."""
    refuse_overlong_prompt(prompt, pinning)
    return {
        MODEL_FIELD: pinning.model,
        "system": prompt.system,
        "prompt": prompt.user,
        "stream": False,
        "format": JSON_REPLY_FORMAT,
        # Beside the options, not among them: Ollama reads `think` at the top level.
        "think": PINNED_THINKING,
        "options": {
            "temperature": PINNED_TEMPERATURE,
            "seed": pinning.seed,
            "num_ctx": pinning.context_tokens,
        },
    }


def estimated_tokens(prompt: Question) -> int:
    """Estimate what a prompt will cost the model to read, in tokens."""
    return (len(prompt.system) + len(prompt.user)) // CHARACTERS_PER_TOKEN


def refuse_overlong_prompt(prompt: Question, pinning: LocalModel) -> None:
    """Refuse a prompt the window cannot hold, rather than let the server cut it in silence."""
    estimated = estimated_tokens(prompt)
    usable = int(pinning.context_tokens * USABLE_CONTEXT_FRACTION)
    if estimated <= usable:
        return
    raise ValueError(
        f"This {prompt.subject} prompt is roughly {estimated} tokens, about "
        f"{estimated - usable} more than the {usable} usable of the {pinning.context_tokens} "
        f"{pinning.model} is pinned to. Ollama would cut it without saying so and the member "
        f"would assess part of the advisory as though it were all of it. Shorten the "
        f"advisory, or raise the pinned context knowing it changes what the run compares to."
    )


def refuse_cut_prompt(counted: Any, prompt: Question, pinning: LocalModel) -> None:
    """Refuse an answer to a prompt the server read only part of, having cut it without an error."""
    # A server reporting no count cannot be held to one.
    if not isinstance(counted, int):
        return
    estimated = estimated_tokens(prompt)
    if counted >= estimated * CUT_PROMPT_FRACTION:
        return
    raise ModelUnavailable(
        f"{pinning.model} read this {prompt.subject} prompt as {counted} tokens, where about "
        f"{estimated} were sent: Ollama cut it to fit the {pinning.context_tokens} pinned, and "
        f"an answer to part of an advisory is not an answer to the advisory"
    )


def refuse_remote_host(host: str) -> None:
    """Refuse a host that is neither this machine nor the server elsewhere the operator chose."""
    if on_this_machine(host):
        return
    chosen = current_settings()
    if chosen.remote_opted_in and host == chosen.server:
        return
    raise ValueError(
        f"{host!r} is not this machine: an Ollama member may only talk to "
        f"{', '.join(LOOPBACK_HOSTS[:2])}, or to the one server {REMOTE_SERVER}=yes lets the "
        "settings name. A model elsewhere is a hosted member."
    )
