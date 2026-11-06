"""What the audit command takes.

The repository is an argument; nothing clones it, since fetching and scanning need
the proxy in opposite directions. The council is off unless `--council` or
`--council-member` asks for one, and both at once are refused. When on, it is scoped
to findings whose sources do not settle them, unless `--council-all-findings` turns
that off.
"""

import argparse
from dataclasses import dataclass
from pathlib import Path

from council.env_file import COUNCIL_MEMBERS, SERVER

PROGRAM = "audit"
# The scan is offline, but a council reaches a server, so don't call the run offline.
DESCRIPTION = (
    "Audit a repository against the pinned advisory database, offline; a council, "
    f"when one runs, asks the Ollama server {SERVER} names."
)

TEXT_FORMAT = "text"
JSON_FORMAT = "json"
HTML_FORMAT = "html"
REPORT_FORMATS = (TEXT_FORMAT, JSON_FORMAT, HTML_FORMAT)

REPOSITORY_HELP = "the repository to audit, already on disk"
FORMAT_HELP = (
    "text for a terminal, json for the audit record, "
    "html for one self-contained page that fetches nothing"
)
ANSWERS_HELP = (
    "a JSON file of this organisation's answers to the approved questions; "
    "without one no Organisation Risk Score is computed and the report says so"
)
# Not "local": AUDITOR_REMOTE_SERVER=yes can put the server on another machine.
MEMBER_HELP = (
    f"add one model on the Ollama server {SERVER} names to the assessor council, "
    "by its Ollama name; repeat for more members, and give none to run no council"
)
COUNCIL_HELP = (
    f"run the assessor council with the models {COUNCIL_MEMBERS} names, in the environment "
    f"or .env, comma-separated, on the Ollama server {SERVER} names"
)
ALL_FINDINGS_HELP = (
    "put every finding to the council, not only those whose published sources "
    "disagree, include one that could not be read, or scored nothing; slower, "
    "and the only way to catch two sources that agree and are both wrong"
)
# A separate mode: record a decision on a finished report instead of auditing one.
APPROVE_HELP = (
    "record a decision on a report this tool already wrote, without auditing again; "
    "names its JSON, reads the decision from --answers, and rewrites the three reports"
)
REPLACE_APPROVAL_HELP = (
    "replace a decision a report already carries; without it an approved report is "
    "refused rather than overwritten"
)
# Without members the flag would change nothing but read as if every finding was asked.
ALL_FINDINGS_WITHOUT_MEMBERS = (
    "--council-all-findings needs --council or a --council-member: with nobody named "
    "there is no council to put the findings to"
)
# A terminal gets a progress bar by default; this asks for the full per-call log instead.
DEBUG_HELP = (
    "print one line per model call, as a council run does when the error stream is "
    "redirected, instead of the progress bar a terminal gets"
)
# Taking one over the other would be a precedence the operator never chose.
BOTH_COUNCILS = (
    f"--council runs the members {COUNCIL_MEMBERS} names and --council-member names "
    "them here; give one or the other, not both"
)
# The two modes are separate; mixing their flags asks for one and describes the other.
NO_REPOSITORY = "a repository to audit is required, unless --approve names a report to record on"
APPROVE_WITH_REPOSITORY = "give a repository to audit or --approve a saved report, not both"
APPROVE_NEEDS_ANSWERS = "--approve needs --answers: the decision is read from the answers file"
APPROVE_TAKES_NO_FORMAT = "--approve rewrites all three reports, so --format chooses nothing"
APPROVE_TAKES_NO_COUNCIL = "--approve runs no council: it records a decision, it does not audit"
APPROVE_TAKES_NO_DEBUG = "--approve makes no model call, so --debug has no per-call log to print"
REPLACE_APPROVAL_NEEDS_APPROVE = "--replace-approval needs --approve; no report to replace one on"


@dataclass(frozen=True)
class Options:
    """One invocation: what to audit, how to report it, and who to ask about it."""

    # None only when `--approve` names a report instead; `parse_arguments` refuses both.
    repository: Path | None
    report_format: str
    council_models: tuple[str, ...]
    council_all_findings: bool = False
    # `--council`: the members are the setting's, read by `cli.audit` when it runs.
    council_from_settings: bool = False
    # None means no file was given; `organisation_run` reads it as that.
    answers: Path | None = None
    # The full per-call log instead of a terminal's progress bar;
    # `cli.progress_bar.bar_for` chooses between them.
    debug: bool = False
    # The saved report JSON to record a decision on, or None for an audit;
    # `cli.main` dispatches to `cli.approve` when it is set.
    approve: Path | None = None
    # Replace a decision a report already carries, rather than refuse it.
    replace_approval: bool = False


def parse_arguments(argv: list[str] | None = None) -> Options:
    """Read one command line into the options an audit, or an approval, runs with."""
    parser = build_parser()
    parsed = parser.parse_args(argv)
    check_mode(parser, parsed)
    return Options(
        repository=Path(parsed.repository) if parsed.repository else None,
        report_format=parsed.format or TEXT_FORMAT,
        council_models=tuple(parsed.council_member),
        council_all_findings=parsed.council_all_findings,
        council_from_settings=parsed.council,
        answers=Path(parsed.answers) if parsed.answers else None,
        debug=parsed.debug,
        approve=Path(parsed.approve) if parsed.approve else None,
        replace_approval=parsed.replace_approval,
    )


def check_mode(parser: argparse.ArgumentParser, parsed: argparse.Namespace) -> None:
    """Refuse a command line that mixes the two modes, or that leaves one short of a flag."""
    if parsed.approve:
        check_approve(parser, parsed)
        return
    # Before the repository check, so `--replace-approval` with no `--approve` names itself.
    if parsed.replace_approval:
        parser.error(REPLACE_APPROVAL_NEEDS_APPROVE)
    if not parsed.repository:
        parser.error(NO_REPOSITORY)
    if parsed.council and parsed.council_member:
        parser.error(BOTH_COUNCILS)
    if parsed.council_all_findings and not (parsed.council or parsed.council_member):
        parser.error(ALL_FINDINGS_WITHOUT_MEMBERS)


def check_approve(parser: argparse.ArgumentParser, parsed: argparse.Namespace) -> None:
    """Refuse an approval that also audits, or that carries a flag the mode cannot act on."""
    if parsed.repository:
        parser.error(APPROVE_WITH_REPOSITORY)
    if not parsed.answers:
        parser.error(APPROVE_NEEDS_ANSWERS)
    if parsed.format is not None:
        parser.error(APPROVE_TAKES_NO_FORMAT)
    if parsed.council or parsed.council_member or parsed.council_all_findings:
        parser.error(APPROVE_TAKES_NO_COUNCIL)
    if parsed.debug:
        parser.error(APPROVE_TAKES_NO_DEBUG)


def build_parser() -> argparse.ArgumentParser:
    """Describe the command line, so `--help` is the documentation."""
    parser = argparse.ArgumentParser(prog=PROGRAM, description=DESCRIPTION)
    # Optional: `--approve` names a report instead, and `parse_arguments` refuses neither
    # or both. The default format is resolved there, so `--approve` can tell it from none.
    parser.add_argument("repository", nargs="?", default=None, help=REPOSITORY_HELP)
    parser.add_argument(
        "--format", choices=REPORT_FORMATS, default=None, help=FORMAT_HELP
    )
    parser.add_argument(
        "--council-member", action="append", default=[], metavar="MODEL", help=MEMBER_HELP
    )
    parser.add_argument("--council", action="store_true", help=COUNCIL_HELP)
    parser.add_argument(
        "--council-all-findings", action="store_true", help=ALL_FINDINGS_HELP
    )
    parser.add_argument("--answers", metavar="FILE", default=None, help=ANSWERS_HELP)
    parser.add_argument("--debug", action="store_true", help=DEBUG_HELP)
    parser.add_argument("--approve", metavar="REPORT_JSON", default=None, help=APPROVE_HELP)
    parser.add_argument("--replace-approval", action="store_true", help=REPLACE_APPROVAL_HELP)
    return parser
