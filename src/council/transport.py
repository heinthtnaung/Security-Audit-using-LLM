"""Post one JSON request to a model server, behind a seam a test can replace.

Every member call goes through `post_json` and the two server reads through
`get_json`; nothing else here opens a socket. No proxy, ever: a corporate proxy
answers 127.0.0.1 with a 502 that looks like the server being down. No redirect,
ever: a followed redirect would return another host's answer as the server's.
Keeping a call on loopback is guaranteed one layer up (`council.ollama`,
`council.settings`), not here.
"""

import http.client
import json
import urllib.error
import urllib.request
from email.message import Message
from typing import IO, Any, Protocol

from council.settings import current_settings

JSON_CONTENT_TYPE = "application/json"

# Enough of a server's complaint to act on, without a body in an exception.
BODY_EXCERPT_CHARACTERS = 400

# A 3xx is an answer from somewhere else, and nothing here goes to fetch it.
REDIRECT_CODES = range(300, 400)
LOCATION_HEADER = "Location"


class RefuseRedirects(urllib.request.HTTPRedirectHandler):
    """Follow no redirect, so every reply comes from the URL the caller named."""

    def redirect_request(
        self, req: urllib.request.Request, fp: IO[bytes], code: int, msg: str,
        headers: Message, newurl: str,
    ) -> None:
        """Decline the redirect: `urllib` then raises the 3xx as the answer it is."""
        return None


NO_PROXY_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}), RefuseRedirects())


class ModelUnavailable(RuntimeError):
    """Nothing usable came back from a model server, for any reason.

    Raised here when the server could not be reached, timed out, redirected, sent
    malformed HTTP, or did not return JSON, and in `council.envelope` when a server
    that answered refused, cut the model off, or sent no text. One exception for
    all of them: that member has no answer, and `council.runner` asks the others.
    """


class Transport(Protocol):
    """Post a JSON payload to a URL and give back the JSON that came home."""

    def __call__(self, url: str, payload: dict[str, Any]) -> Any:
        """Post one request and return the parsed reply envelope."""


def post_json(url: str, payload: dict[str, Any], timeout: float | None = None) -> Any:
    """Post a JSON payload and give back the parsed reply, refusing anything else.

    With no `timeout` given, the operator's `AUDITOR_TIMEOUT_SECONDS` is waited.
    """
    return fetch_json(url, build_request(url, payload), timeout)


def get_json(url: str, timeout: float) -> Any:
    """Read one JSON document from the model server, such as its version, refusing anything else."""
    return fetch_json(url, url, timeout)


def fetch_json(url: str, request: urllib.request.Request | str, timeout: float | None) -> Any:
    """Send one request around the proxy and parse the JSON that comes back, or fail saying why."""
    timeout = current_settings().timeout_seconds if timeout is None else timeout
    try:
        with NO_PROXY_OPENER.open(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as fault:
        raise ModelUnavailable(http_failure_message(url, fault)) from fault
    except (urllib.error.URLError, OSError) as fault:
        raise ModelUnavailable(unanswered_message(url, fault, timeout)) from fault
    # After OSError, so a RemoteDisconnected (both) is named as not reached.
    except http.client.HTTPException as fault:
        raise ModelUnavailable(f"{url} sent a malformed HTTP reply: {fault!r}") from fault
    return read_json(url, body)


def build_request(url: str, payload: dict[str, Any]) -> urllib.request.Request:
    """Build the POST carrying one JSON payload."""
    encoded = json.dumps(payload).encode("utf-8")
    return urllib.request.Request(
        url, data=encoded, headers={"Content-Type": JSON_CONTENT_TYPE}, method="POST"
    )


def unanswered_message(url: str, fault: OSError, timeout: float) -> str:
    """Say why nothing came back: a server too slow for the timeout, or none there at all."""
    # A model too big for this machine looks like a slow server; word them differently.
    if isinstance(getattr(fault, "reason", fault), TimeoutError):
        return f"{url} did not answer within {timeout:g} s: {fault}"
    return f"{url} could not be reached: {fault}"


def http_failure_message(url: str, fault: urllib.error.HTTPError) -> str:
    """Say that a server refused or redirected the request, quoting the start of what it said."""
    if fault.code in REDIRECT_CODES:
        return redirect_message(url, fault)
    body = fault.read().decode("utf-8", errors="replace")[:BODY_EXCERPT_CHARACTERS]
    return f"{url} answered {fault.code}: {body.strip() or fault.reason}"


def redirect_message(url: str, fault: urllib.error.HTTPError) -> str:
    """Say where a server sent the request, and that nothing went there."""
    where = fault.headers.get(LOCATION_HEADER) or "no location"
    return (
        f"{url} answered {fault.code}, a redirect to {where}, which is not followed: "
        "the server the settings name must answer itself"
    )


def read_json(url: str, body: str) -> Any:
    """Parse a reply envelope, refusing a server that did not return the JSON it promised."""
    try:
        return json.loads(body)
    except ValueError as fault:
        excerpt = body[:BODY_EXCERPT_CHARACTERS]
        raise ModelUnavailable(f"{url} did not return JSON: {fault}\n{excerpt}") from fault
