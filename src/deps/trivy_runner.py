"""Trivy: the advisories published against a directory's components, and its secrets.

A thin wrapper, offline by construction, that runs the tool once and hands the JSON
to `deps.trivy_report` and `deps.trivy_secrets`. One run finds both: the secret
scanner reads no database and rides on the same offline run. Every flag that keeps
the scan offline lives in one tuple no call site can skip.
"""

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from deps.scanner import (
    ScannerFailed,
    as_directory,
    refuse_missing_directory,
    run_json_scanner,
    run_scanner,
)
from deps.trivy_report import Advisory, read_advisories
from deps.trivy_secrets import SecretFinding, read_secrets

TRIVY_EXECUTABLE = "trivy"
FILESYSTEM_SUBCOMMAND = "fs"
JSON_FORMAT = ("--format", "json")
VULNERABILITIES_AND_SECRETS = ("--scanners", "vuln,secret")
# Built-in secret rules only; an empty path is Trivy's way of saying so. Its default
# reads a `trivy-secret.yaml` that could silently disable a rule (measured on 0.74.0).
BUILT_IN_SECRET_RULES = ("--secret-config=",)
VERSION_FLAG = "--version"
CACHE_FLAG = "--cache-dir"

# Trivy's own version is unindented under this prefix; the schema version is indented.
VERSION_PREFIX = "Version:"

# The offline guarantee, in one place. Trivy exits non-zero on a flag it drops, so a
# removed flag fails the run loudly rather than letting a scan reach the network.
REQUIRED_OFFLINE_FLAGS: tuple[str, ...] = (
    "--skip-db-update",
    "--offline-scan",
    "--disable-telemetry",
    "--skip-version-check",
)


def is_available() -> bool:
    """Say whether Trivy is installed, so a caller can report no advisories rather than fail."""
    return shutil.which(TRIVY_EXECUTABLE) is not None


def installed_version() -> str:
    """Give the Trivy version on this machine, as Trivy itself reports it."""
    said = run_scanner([TRIVY_EXECUTABLE, VERSION_FLAG])
    for line in said.splitlines():
        if line.startswith(VERSION_PREFIX):
            return line.removeprefix(VERSION_PREFIX).strip()
    raise ScannerFailed(f"{TRIVY_EXECUTABLE} did not say which version it is: {said.strip()!r}")


@dataclass(frozen=True)
class TrivyScan:
    """What one Trivy run found: advisories by the purl they were raised against, and secrets."""

    advisories: Mapping[str, tuple[Advisory, ...]]
    secrets: tuple[SecretFinding, ...]


def scan_directory(directory: str | Path, cache: Path) -> TrivyScan:
    """Run Trivy over a directory against one cache, and give its advisories and its secrets."""
    scanned = as_directory(directory)
    refuse_missing_directory(scanned)
    report = run_json_scanner(build_command(scanned, cache))
    return TrivyScan(advisories=read_advisories(report), secrets=read_secrets(report))


def build_command(directory: Path, cache: Path) -> list[str]:
    """Build the Trivy command line for one directory, offline by construction."""
    return [
        TRIVY_EXECUTABLE,
        FILESYSTEM_SUBCOMMAND,
        *JSON_FORMAT,
        *VULNERABILITIES_AND_SECRETS,
        *BUILT_IN_SECRET_RULES,
        *REQUIRED_OFFLINE_FLAGS,
        CACHE_FLAG,
        str(cache),
        str(directory),
    ]
