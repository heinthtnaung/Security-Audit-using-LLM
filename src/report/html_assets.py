"""The page's stylesheet and script, read from package data and inlined whole.

Read through `importlib.resources` at render time, so an installed copy and a source checkout
behave alike. The stylesheet is four files joined in a fixed order. Both are inlined, never
linked: a scan runs offline, so a fetched asset would arrive unreadable.
"""

from importlib.resources import files

ASSET_FOLDER = "assets"
STYLESHEET_FILES = ("tokens.css", "layout.css", "components.css", "media.css")
SCRIPT_FILE = "report.js"


def read_asset(name: str) -> str:
    """Read one packaged asset in full, so the page carries exactly what shipped."""
    return files("report").joinpath(ASSET_FOLDER, name).read_text(encoding="utf-8")


def stylesheet() -> str:
    """Join the stylesheet's files in their fixed order, to be inlined in the one `<style>`."""
    return "\n".join(read_asset(name) for name in STYLESHEET_FILES)


def script() -> str:
    """Give the whole script, to be inlined in the page's one `<script>`."""
    return read_asset(SCRIPT_FILE)
