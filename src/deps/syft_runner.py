"""Syft: the components a directory declares, in this project's terms.

A thin wrapper that runs the tool and hands the JSON to `deps.syft_report`. Syft
missing is a normal answer, not a crash; ask `is_available` first.
"""

import shutil
from pathlib import Path

from deps.scanner import as_directory, refuse_missing_directory, run_json_scanner, run_scanner
from deps.syft_report import Catalogue, read_catalogue

SYFT_EXECUTABLE = "syft"
SCAN_SUBCOMMAND = "scan"
DIRECTORY_SCHEME = "dir:"
JSON_FORMAT = ("-o", "syft-json")
VERSION_FLAG = "--version"


def is_available() -> bool:
    """Say whether Syft is installed, so a caller can report no components rather than fail."""
    return shutil.which(SYFT_EXECUTABLE) is not None


def installed_version() -> str:
    """Give the Syft version on this machine, as Syft itself reports it."""
    # Asked, not configured: a typed version is a claim nobody checked.
    said = run_scanner([SYFT_EXECUTABLE, VERSION_FLAG]).strip()
    return said.removeprefix(f"{SYFT_EXECUTABLE} ").strip() or said


def scan_directory(directory: str | Path) -> Catalogue:
    """Run Syft over a directory and give what it catalogued, joinable or not."""
    scanned = as_directory(directory)
    refuse_missing_directory(scanned)
    return read_catalogue(run_json_scanner(build_command(scanned)))


def build_command(directory: Path) -> list[str]:
    """Build the Syft command line for one directory."""
    return [
        SYFT_EXECUTABLE,
        SCAN_SUBCOMMAND,
        f"{DIRECTORY_SCHEME}{directory}",
        *JSON_FORMAT,
    ]
