"""The local model server's settings: an environment variable wins, then `.env`, then the default.

Five `AUDITOR_*` settings: the model to ask where none is named, the Ollama server,
the opt-in to a server on another machine (`AUDITOR_REMOTE_SERVER=yes`), the call
timeout, and the context window. Whether a run was local is read off the server's
host, not the opt-in. Temperature, seed and `think` are not settings; they stay
pinned in `council.ollama` to keep a local member reproducible.
"""

import math
import os
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Callable, Mapping
from urllib.parse import urlsplit

from council.env_file import (
    CONTEXT,
    FROM_ENVIRONMENT,
    MODEL,
    REMOTE_SERVER,
    SERVER,
    TIMEOUT,
    SettingsError,
    auditor_lines,
    refuse_unknown_names,
)
from council.server_address import DEFAULT_ADDRESS, address_of

# Looked up each time a setting is read, so a test can point it at no file.
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

# The window default is measured: the worst advisory's prompt is ~4,900-5,700
# tokens across models, so 8192 holds it. Moving it changes what a run compares
# to, so the record states the window a run used.
DEFAULTS = {
    MODEL: "qwen2.5:7b-instruct",
    SERVER: DEFAULT_ADDRESS,
    # Unset or empty: the server stays on this machine.
    REMOTE_SERVER: "",
    TIMEOUT: "180",
    CONTEXT: "8192",
}

LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")
# The one value that lets the server be another machine; `true` or `1` is refused.
REMOTE_OPT_IN = "yes"
FROM_DEFAULT = "the default"


@dataclass(frozen=True)
class Settings:
    """The five settings a run of the model server uses; one on this machine need not opt in."""

    model: str
    server: str
    timeout_seconds: float
    context_tokens: int
    remote_opted_in: bool = False


@cache
def current_settings() -> Settings:
    """Give this process's settings, read once, so a run cannot change them part way."""
    return load_settings(os.environ, ENV_FILE)


def load_settings(environment: Mapping[str, str], env_file: Path) -> Settings:
    """Read the five settings: an environment variable wins, then `.env`, then the default."""
    refuse_unknown_names(environment, FROM_ENVIRONMENT)
    from_file = auditor_lines(env_file)
    chosen = {name: chosen_value(name, environment, from_file) for name in DEFAULTS}
    remote_opted_in = opted_in(*chosen[REMOTE_SERVER])
    return Settings(
        model=model_of(*chosen[MODEL]),
        server=server_of(*chosen[SERVER], remote_opted_in),
        timeout_seconds=positive(TIMEOUT, *chosen[TIMEOUT], float),
        context_tokens=positive(CONTEXT, *chosen[CONTEXT], int),
        remote_opted_in=remote_opted_in,
    )


def chosen_value(
    name: str, environment: Mapping[str, str], from_file: Mapping[str, tuple[str, str]]
) -> tuple[str, str]:
    """Give one setting's value and where it came from."""
    if name in environment:
        return environment[name], FROM_ENVIRONMENT
    return from_file.get(name, (DEFAULTS[name], FROM_DEFAULT))


def model_of(value: str, source: str) -> str:
    """Give the model to ask where none is named, refusing no name at all."""
    if not value.strip():
        raise SettingsError(f"{MODEL} is empty ({source}); name a model as `ollama list` does")
    return value.strip()


def opted_in(value: str, source: str) -> bool:
    """Say whether the operator opted in to a server elsewhere, refusing all but `yes` or none."""
    if value.strip() == REMOTE_OPT_IN:
        return True
    if not value.strip():
        return False
    raise SettingsError(
        f"{REMOTE_SERVER} is {value!r} ({source}); only `{REMOTE_OPT_IN}` enables it, letting "
        f"{SERVER} name another machine, and unset or empty leaves it off"
    )


def server_of(value: str, source: str, remote_opted_in: bool) -> str:
    """Give the server's address, the old form with its endpoint accepted, refusing any other."""
    # Its shape is `council.server_address`'s; where it may be is this file's.
    address = address_of(value, source)
    if remote_opted_in or on_this_machine(address):
        return address
    raise SettingsError(
        f"{SERVER} is {value!r} ({source}), which is not this machine: a local member "
        f"may only talk to {', '.join(LOOPBACK_HOSTS[:2])}; set {REMOTE_SERVER}={REMOTE_OPT_IN} "
        "to send the advisory text to that machine"
    )


def on_this_machine(server: str) -> bool:
    """Say whether a server's address is this machine's own."""
    return not remote_host(server)


def remote_host(server: str) -> str:
    """Give the host of a server on another machine, and nothing for this machine's own."""
    hostname = urlsplit(server).hostname
    if not hostname:
        raise SettingsError(f"{server!r} names no host, so nothing can say which machine it is")
    return "" if hostname in LOOPBACK_HOSTS else hostname


def positive(name: str, value: str, source: str, kind: Callable[[str], float]) -> float:
    """Give a setting as a positive number of the kind asked for, refusing anything else."""
    wanted = "whole number" if kind is int else "number"
    refusal = SettingsError(f"{name} is {value!r} ({source}); it must be a positive {wanted}")
    try:
        number = kind(value.strip())
    except ValueError:
        raise refusal from None
    if not math.isfinite(number) or number <= 0:
        raise refusal
    return number
