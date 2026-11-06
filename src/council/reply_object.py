"""Find the one JSON object in what a member said, or refuse the reply loudly.

Prose around the object is tolerated; the object is still the object. A second
object is not: a model that drafts and then answers leaves two, and which one it
meant is not for this code to guess, so neither is read.
"""

import json
from typing import Any, Mapping

OBJECT_START = "{"

# Enough of a reply to see what went wrong, without a page of prose in a message.
REPLY_EXCERPT_CHARACTERS = 300

Decoded = tuple[Mapping[str, Any], int]


class MalformedReply(ValueError):
    """A member's reply was not the JSON object the prompt asked for."""


def extract_object(text: str) -> Mapping[str, Any]:
    """Find the one JSON object in a reply, ignoring prose around it and refusing a second."""
    if not isinstance(text, str) or not text.strip():
        raise MalformedReply("A member answered with nothing at all")
    found = objects_in(text)
    if not found:
        raise MalformedReply(f"No complete JSON object in the reply -- {excerpt(text)}")
    if len(found) > 1:
        raise MalformedReply(f"The reply holds {len(found)} JSON objects -- {excerpt(text)}")
    return found[0]


def objects_in(text: str) -> list[Mapping[str, Any]]:
    """Give every JSON object in a text that is not inside another, in order."""
    decoder, found = json.JSONDecoder(), []
    start = text.find(OBJECT_START)
    while start != -1:
        decoded = decode_at(decoder, text, start)
        if decoded is None:
            start = text.find(OBJECT_START, start + 1)
            continue
        found.append(decoded[0])
        start = text.find(OBJECT_START, decoded[1])
    return found


def decode_at(decoder: json.JSONDecoder, text: str, start: int) -> Decoded | None:
    """Decode a JSON object starting at one offset, with where it ends, or say it is not one."""
    try:
        found, end = decoder.raw_decode(text, start)
    except ValueError:
        return None
    return (found, end) if isinstance(found, Mapping) else None


def excerpt(text: str) -> str:
    """Quote the start of a reply, so a refusal says what was actually said."""
    shown = " ".join(str(text).split())[:REPLY_EXCERPT_CHARACTERS]
    return f"the reply began {shown!r}"
