# Security-Audit-using-LLM

Audit a code repository for vulnerable components and leaked secrets, offline,
then score each finding against your own environment.

Security-Audit-using-LLM lists a repository's components with Syft, matches them
against an offline Trivy advisory database, and scores every published CVSS v3.1
vector one source at a time. The same Trivy run reports where a secret sits,
without printing the secret. Answer twelve questions about your environment and
it adds an Organisation Risk Score. Name local Ollama models and a council reads
each disputed advisory, quoting the text behind every value it gives.

## Table of contents

- [About](#about)
- [Built with](#built-with)
- [Getting started](#getting-started)
- [Usage](#usage)
- [Settings](#settings)
- [Exit codes](#exit-codes)
- [License](#license)

## About

The tool scans a repository that is already on disk. Syft builds the component
inventory, Trivy matches each component against a pinned advisory database and
runs its built-in secret rules, and a deterministic engine scores every
published CVSS v3.1 vector. The scan is offline: it reads the database but never
updates it.

Give it a JSON file of answers about your environment and it adds an
Organisation Risk Score from 0 to 100 for each finding. Name local models and a
council reads each advisory whose published sources disagree, then reports the
vector the members settle, backed by a quotation from the advisory itself.

Every number comes from a deterministic engine. The CVSS scores use the standard
CVSS v3.1 equations; the Organisation Risk Score weights your answers by
category. No model, clock or network changes a score. A council adds its reading
beside the published scores and never overwrites one. Secrets are reported by
location only.

## Built with

- Python standard library, with no runtime dependencies
- [Syft](https://github.com/anchore/syft), to list the components
- [Trivy](https://trivy.dev), to match advisories and find secrets, offline
- [Ollama](https://ollama.com), to run the optional council of local models

## Getting started

### Prerequisites

| Tool | For | Tested with | Minimum |
|---|---|---|---|
| Python | everything | 3.11.11 | 3.11 |
| Syft | listing the components | 1.52.0 | none set |
| Trivy | matching advisories and finding secrets | 0.74.0 | none set |
| Ollama | the council (optional) | 0.34.3 | none set |

Download the advisory database once. This needs network access, so on a
corporate network the proxy must be **on**:

```bash
trivy image --download-db-only
```

It lands in `$TRIVY_CACHE_DIR` if set, else `$XDG_CACHE_HOME/trivy`, else
`~/.cache/trivy`. Scans read it offline and never update it. Run the download
again to update it.

### Install

Clone the repository and change into it:

```bash
git clone https://github.com/heinthtnaung/Security-Audit-using-LLM.git
cd Security-Audit-using-LLM
```

Then create a virtual environment and install:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
```

This puts the `audit` command on your path. The install fetches a build backend,
so it needs network access too.

### Get a repository to scan

The examples below scan `fetched/vulnscout`, the repository this project audits.
Fetch it once:

```bash
git clone https://github.com/savoirfairelinux/vulnscout.git fetched/vulnscout
```

Cloning needs network access, so the proxy must be **on** for it. `audit` never
clones anything: point it at any directory already on disk.

## Usage

`audit` has two forms: one audits a repository, the other records a decision on a
report it already wrote.

```text
# audit a repository
audit REPOSITORY [--format {text,json,html}] [--answers FILE]
      [(--council | --council-member MODEL ...) [--council-all-findings]] [--debug]

# record a decision on a report already written
audit --approve REPORT_JSON --answers FILE [--replace-approval]
```

A worked run on the example repository:

```bash
# scan the repository
audit fetched/vulnscout

# scan and score it against your environment
audit fetched/vulnscout --answers answers.json

# scan with a council of named models
audit fetched/vulnscout --council-member qwen2.5:7b-instruct --council-member llama3.2:latest

# record an approval on the saved report, without scanning again
audit --approve reports/vulnscout.json --answers answers.json
```

All three report files are always saved; the options change what runs and what
prints on stdout.

| Option | What it does | Example |
|---|---|---|
| `REPOSITORY` | the directory to audit, already on disk | `audit fetched/vulnscout` |
| `--format {text,json,html}` | choose what prints on stdout; default `text` | `audit fetched/vulnscout --format json` |
| `--answers FILE` | score findings against your environment from a JSON answers file | `audit fetched/vulnscout --answers answers.json` |
| `--council` | run the council named by `AUDITOR_COUNCIL_MEMBERS` in the environment or `.env` | `audit fetched/vulnscout --council` |
| `--council-member MODEL` | add one council member by its Ollama name; repeat for more, and not with `--council` | `audit fetched/vulnscout --council-member qwen2.5:7b-instruct` |
| `--council-all-findings` | put every finding to the council, not only disputed ones; needs a council | `audit fetched/vulnscout --council --council-all-findings` |
| `--debug` | print one line per model call instead of the progress bar | `audit fetched/vulnscout --council --debug` |
| `--approve REPORT_JSON` | record a decision on a report already written, without auditing; needs `--answers` and refuses `--format`, `--council`, `--council-member`, `--council-all-findings` and `--debug` | `audit --approve reports/vulnscout.json --answers answers.json` |
| `--replace-approval` | replace a decision a report already carries; needs `--approve` | `audit --approve reports/vulnscout.json --answers answers.json --replace-approval` |

Model names above are examples; any model pulled into your local Ollama works.

### Scan a repository

```bash
audit fetched/vulnscout
```

This prints the text report and saves it as text, JSON and HTML in `reports/`,
named after the directory. The HTML is one self-contained page that opens in a
browser offline. The last line on stderr says where:
`reports written to reports/vulnscout.txt, reports/vulnscout.json, reports/vulnscout.html`.

The sample output below is an example; your numbers will differ with the
repository version and the advisory database date.

<!-- doc-check: run (elided) -->
```
Audit of fetched/vulnscout
  syft 1.52.0  ·  trivy 0.74.0  ·  advisory database built 2026-09-23T20:20:57.734988316Z
  scoring rules ors-1

18 findings across 60 components. 5 carry sources that disagree.
Approval is needed for 5 of 18: sources that disagree. With no organisation answers, no finding
was checked for a High or Critical Organisation Risk Score. No approval is recorded for this
audit.
0 secrets matched the secret rules built into Trivy.

SOURCES DISAGREE (5)
  CVE-2025-13465  lodash-es 4.17.21
    2.9 apart  ·  High and Medium  ·  differ on A
    ghsa 6.5  ·  nvd 5.3  ·  redhat 8.2

SOURCES AGREE (13)
  CVE-2026-14257       brace-expansion 1.1.14          7.5  High      2 sources

SECRETS (0)
  Trivy's built-in secret rules matched nothing in this tree.

NOT ASSESSED
  Organisation Risk Score
    no organisation answers were supplied, so no environment was weighed
  Approval record
    no answer file was given, so nobody was asked about this environment
  Council ruling
    no council assessed this run, so no council reading stands beside the published scores
  Why the sources differ
    no council was asked for, so no model was asked why the published sources differ
```

The block above is a selection: four of the five disagreements, twelve of the
thirteen agreements, and the `MATCHED NOTHING` and `NEEDS APPROVAL` blocks are
left out. What is not assessed is named, never printed as a zero. This run was
not asked the questions: its input was piped in, or it ran in CI.

### Score it against your environment

Answer the twelve approved questions in a JSON file.
[`answers.example.json`](answers.example.json) is a skeleton with every answer
`No`. Here it is filled in for an internet-facing, business-critical asset:

<!-- doc-check: answers -->
```json
{
  "answers": {
    "EXP-1": "Yes", "EXP-2": "Yes", "EXP-3": "Yes", "EXP-4": "No", "EXP-5": "No",
    "BUS-1": "Yes", "BUS-2": "Yes", "BUS-3": "Yes", "BUS-4": "Yes",
    "THR-1": "No",  "THR-2": "No",  "THR-3": "No"
  },
  "by_advisory": {
    "CVE-2021-4279": {"THR-1": "Yes", "THR-2": "Yes"}
  },
  "approval": {
    "approver": "Hein",
    "decision": "approved",
    "recorded_at": "2026-09-23T09:15:00Z",
    "note": "reviewed against the staging inventory"
  }
}
```

```bash
audit fetched/vulnscout --answers answers.json
```

This adds an Organisation Risk Score, 0 to 100, for each published source:

<!-- doc-check: run --answers -->
```
ORGANISATION RISK (18)  ·  the source changes the band on 1
  weighted Technical severity 0.3, Exposure and reachability 0.25, Business impact 0.25, Threat and exploitation 0.2
  CVE-2026-4800        ghsa 70.5 to nvd 75.7       Critical and High
  CVE-2021-4279        ghsa 84.2 to nvd 91.7       Critical
  CVE-2025-13465       nvd 62.1 to redhat 70.8     High
  CVE-2026-13149       ghsa 62.1 to redhat 68.8    High
  CVE-2026-13676       68.8                        High
  CVE-2026-14257       68.8                        High
```

A range runs from one source's score to another's, and the heading counts the
findings whose band depends on which source you believe.

With both stdin and stderr on a terminal and no `--answers`, the tool asks the
twelve questions before the scan, one per line on stderr like
`EXP-1 Is the affected service internet-facing? [y/n/U]`. Answer `y`, `n` or `u`,
or press Enter for Unknown. The replies are saved to
`reports/<name>.answers.json`, so `--answers` on that file reproduces the score.

### Approve a report without re-running it

A council run is slow and does not reproduce, so you can record a decision on
reports a run already wrote. `audit --approve` reads only the `approval` block
from the answer file and makes no model call. It re-renders the three reports and
rewrites them only if they match what was saved; a report another version wrote,
or one whose files no longer agree, is refused. It exits `0` when it records the
decision and `2` when it refuses.

### Add a council of local models

Pull each model once, then name them:

```bash
ollama pull qwen2.5:7b-instruct
ollama pull llama3.2:latest
audit fetched/vulnscout --council-member qwen2.5:7b-instruct --council-member llama3.2:latest
```

Each model reads the advisory of every finding whose published sources disagree,
and the report adds the vector they settle, or the metrics they could not. Name
the members once in `.env` and run `--council` instead. Set
`AUDITOR_ESCALATION_MODEL` to send each metric the council leaves open to one
larger model. A council's readings should be evaluated on your own models before
you trust them.

## Settings

Seven `AUDITOR_*` keys, read from the environment, then from `.env` at the
project root, then the default. Copy `.env.example` to `.env` to start. `audit`
reads them only on a council run.

| Key | Default | Sets |
|---|---|---|
| `AUDITOR_COUNCIL_MEMBERS` | unset | the models `--council` runs, comma-separated |
| `AUDITOR_ESCALATION_MODEL` | unset | one model on the members' server for what the council leaves open |
| `AUDITOR_SERVER_URL` | `http://127.0.0.1:11434` | the Ollama server; this machine unless `AUDITOR_REMOTE_SERVER` opts in |
| `AUDITOR_REMOTE_SERVER` | unset | `yes` lets the server be another machine; every advisory text is then sent there |
| `AUDITOR_TIMEOUT_SECONDS` | `180` | how long one model call may wait |
| `AUDITOR_CONTEXT_TOKENS` | `8192` | the context window every model is pinned to |
| `AUDITOR_MODEL` | `qwen2.5:7b-instruct` | the default model a client uses when none is named; `audit` names its members, so an audit never uses it |

## Exit codes

| Code | Meaning |
|---|---|
| `0` | ran, catalogued components, found nothing, and read every manifest |
| `1` | ran and found something: a vulnerability or a secret |
| `2` | could not run, or could not save its reports |
| `3` | ran and found nothing, but could not read a manifest or catalogued no component |

A pipeline that passes only on `0` stops on the rest. `audit --approve` uses only
`0`, when it records the decision, and `2`, when it refuses.

## License

MIT. See [`LICENSE`](LICENSE).
