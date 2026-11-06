"""The escalation model: `AUDITOR_ESCALATION_MODEL`, read like every other setting.

An environment variable wins over `.env`; the value is one model name. Unset or
empty means no escalation, never a default model. The name must be a model on the
members' Ollama server, so there is no provider to name and no hosted escalation.
Read only when a council is asked for.
"""

import os
from pathlib import Path
from typing import Mapping

from council import settings
from council.env_file import (
    ESCALATION_MODEL,
    FROM_ENVIRONMENT,
    SettingsError,
    auditor_lines,
    refuse_unknown_names,
)

# What would make one name two, or a name no model has.
NOT_IN_A_NAME = (",", " ", "\t")


def escalation_model() -> str | None:
    """Give the model a council escalates to, or None where none is named."""
    return load_escalation_model(os.environ, settings.ENV_FILE)


def load_escalation_model(environment: Mapping[str, str], env_file: Path) -> str | None:
    """Read the escalation model: an environment variable wins, then `.env`; unset is None."""
    refuse_unknown_names(environment, FROM_ENVIRONMENT)
    from_file = auditor_lines(env_file)
    if ESCALATION_MODEL in environment:
        return model_named(environment[ESCALATION_MODEL], FROM_ENVIRONMENT)
    if ESCALATION_MODEL in from_file:
        return model_named(*from_file[ESCALATION_MODEL])
    return None


def model_named(value: str, source: str) -> str | None:
    """Give the one model a value names, None for an empty one, refusing a list or a spaced name."""
    name = value.strip()
    if not name:
        return None
    if any(mark in name for mark in NOT_IN_A_NAME):
        raise SettingsError(
            f"{ESCALATION_MODEL} is {value!r} ({source}); it names one model, "
            "as `ollama list` gives it"
        )
    return name
