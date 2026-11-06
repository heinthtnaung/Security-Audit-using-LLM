"""What a model server's address may be: http(s), a host, and an optional port.

The old form with its `/api/generate` endpoint is accepted and stripped;
whitespace is dropped. No username, password, query or fragment, each refused by
name. A port must be a whole number from 1 to 65535, or none. `council.settings`
then decides whether the host may be another machine.
"""

from urllib.parse import SplitResult, urlsplit

from council.env_file import SERVER, SettingsError

# This machine's Ollama: the setting's default, and the example every refusal gives.
DEFAULT_ADDRESS = "http://127.0.0.1:11434"
SERVER_SCHEMES = ("http", "https")
# The endpoint an earlier version had operators write.
OLD_ENDPOINT = "/api/generate"
# Parts an address may not carry; "#" goes first so it owns any "?" after it.
USERINFO_MARK = "@"
EXTRA_PARTS = (("#", "a fragment"), ("?", "a query"))
# A port `urlsplit` reads, but one that names no server.
UNREACHABLE_PORT = 0


def address_of(value: str, source: str) -> str:
    """Give the server's address, the old form with its endpoint accepted, refusing any other."""
    refuse_extra_parts(value, source)
    address = value.strip().rstrip("/").removesuffix(OLD_ENDPOINT)
    parts = urlsplit(address)
    if parts.scheme not in SERVER_SCHEMES or not parts.hostname or parts.path:
        raise SettingsError(
            f"{SERVER} is {value!r} ({source}); give the server's address alone, "
            f"as {DEFAULT_ADDRESS}"
        )
    refuse_unusable_port(value, source, parts)
    return address


def refuse_extra_parts(value: str, source: str) -> None:
    """Refuse an address carrying a username or password, a fragment or a query, naming which."""
    # Not quoted: what sits before an "@" may be a password.
    if USERINFO_MARK in value:
        raise SettingsError(
            f"{SERVER} ({source}) has an '{USERINFO_MARK}' in it, so it may carry a username or "
            f"password; give the server's address alone, as {DEFAULT_ADDRESS}. It is not "
            "quoted here in case it holds a secret"
        )
    carried = [part for mark, part in EXTRA_PARTS if mark in value]
    if carried:
        raise SettingsError(
            f"{SERVER} is {value!r} ({source}), which carries {carried[0]}; give the server's "
            f"address alone, as {DEFAULT_ADDRESS}"
        )


def refuse_unusable_port(value: str, source: str, parts: SplitResult) -> None:
    """Refuse a port no server can be reached at: anything but a whole number from 1 to 65535."""
    try:
        reachable = parts.port != UNREACHABLE_PORT
    except ValueError:
        reachable = False
    if reachable:
        return
    raise SettingsError(
        f"{SERVER} is {value!r} ({source}), whose port is not a whole number from 1 to 65535; "
        f"give the address with a port in that range, or none, as {DEFAULT_ADDRESS}"
    )
