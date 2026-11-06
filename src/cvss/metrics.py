"""The CVSS Base metrics, the three Temporal ones, and their legal values.

The parser and the equations share this vocabulary. Base metrics reach the
equations; Temporal metrics are validated and ignored; Environmental metrics are
named only to refuse a vector that carries one.
"""

from dataclasses import dataclass

ATTACK_VECTOR = "AV"
ATTACK_COMPLEXITY = "AC"
PRIVILEGES_REQUIRED = "PR"
USER_INTERACTION = "UI"
SCOPE = "S"
CONFIDENTIALITY = "C"
INTEGRITY = "I"
AVAILABILITY = "A"

EXPLOIT_CODE_MATURITY = "E"
REMEDIATION_LEVEL = "RL"
REPORT_CONFIDENCE = "RC"

SCOPE_UNCHANGED = "U"
SCOPE_CHANGED = "C"

IMPACT_METRICS = (CONFIDENTIALITY, INTEGRITY, AVAILABILITY)


@dataclass(frozen=True)
class Metric:
    """One CVSS metric: its abbreviation, its name in words, and the values it allows."""

    abbreviation: str
    name: str
    values: tuple[str, ...]


# Specification order; `CvssVector.__str__` rebuilds a vector in it, so two
# spellings of one assessment compare equal.
BASE_METRICS: tuple[Metric, ...] = (
    Metric(ATTACK_VECTOR, "Attack Vector", ("N", "A", "L", "P")),
    Metric(ATTACK_COMPLEXITY, "Attack Complexity", ("L", "H")),
    Metric(PRIVILEGES_REQUIRED, "Privileges Required", ("N", "L", "H")),
    Metric(USER_INTERACTION, "User Interaction", ("N", "R")),
    Metric(SCOPE, "Scope", (SCOPE_UNCHANGED, SCOPE_CHANGED)),
    Metric(CONFIDENTIALITY, "Confidentiality", ("H", "L", "N")),
    Metric(INTEGRITY, "Integrity", ("H", "L", "N")),
    Metric(AVAILABILITY, "Availability", ("H", "L", "N")),
)

# The same in v3.0 and v3.1. `X` is "Not Defined", which a vector may state.
TEMPORAL_METRICS: tuple[Metric, ...] = (
    Metric(EXPLOIT_CODE_MATURITY, "Exploit Code Maturity", ("X", "H", "F", "P", "U")),
    Metric(REMEDIATION_LEVEL, "Remediation Level", ("X", "U", "W", "T", "O")),
    Metric(REPORT_CONFIDENCE, "Report Confidence", ("X", "C", "R", "U")),
)

# Each readable metric's values named in words, keyed by abbreviation then value
# letter, from the CVSS v3.1 specification (sections 2 and 3). Each inner mapping
# lists the same letters, in the same order, as the metric's `values`.
VALUE_NAMES: dict[str, dict[str, str]] = {
    ATTACK_VECTOR: {"N": "Network", "A": "Adjacent", "L": "Local", "P": "Physical"},
    ATTACK_COMPLEXITY: {"L": "Low", "H": "High"},
    PRIVILEGES_REQUIRED: {"N": "None", "L": "Low", "H": "High"},
    USER_INTERACTION: {"N": "None", "R": "Required"},
    SCOPE: {SCOPE_UNCHANGED: "Unchanged", SCOPE_CHANGED: "Changed"},
    CONFIDENTIALITY: {"H": "High", "L": "Low", "N": "None"},
    INTEGRITY: {"H": "High", "L": "Low", "N": "None"},
    AVAILABILITY: {"H": "High", "L": "Low", "N": "None"},
    EXPLOIT_CODE_MATURITY: {
        "X": "Not Defined", "H": "High", "F": "Functional",
        "P": "Proof-of-Concept", "U": "Unproven",
    },
    REMEDIATION_LEVEL: {
        "X": "Not Defined", "U": "Unavailable", "W": "Workaround",
        "T": "Temporary Fix", "O": "Official Fix",
    },
    REPORT_CONFIDENCE: {
        "X": "Not Defined", "C": "Confirmed", "R": "Reasonable", "U": "Unknown",
    },
}

ENVIRONMENTAL_METRICS: tuple[str, ...] = (
    "CR", "IR", "AR", "MAV", "MAC", "MPR", "MUI", "MS", "MC", "MI", "MA",
)

METRIC_ORDER: tuple[str, ...] = tuple(metric.abbreviation for metric in BASE_METRICS)

METRICS_BY_ABBREVIATION: dict[str, Metric] = {
    metric.abbreviation: metric for metric in BASE_METRICS
}

# A Base metric by its name in words, spelled exactly as the table above spells it.
METRICS_BY_NAME: dict[str, Metric] = {metric.name: metric for metric in BASE_METRICS}

# Every metric a published vector may carry and still be read.
READABLE_METRICS: dict[str, Metric] = {
    metric.abbreviation: metric for metric in (*BASE_METRICS, *TEMPORAL_METRICS)
}


def metric_name(abbreviation: str) -> str:
    """Give a Base metric's name in words, so a refusal reads as English."""
    # ValueError, not the dict's KeyError: callers wrap vector work in `except ValueError`.
    metric = METRICS_BY_ABBREVIATION.get(abbreviation)
    if metric is None:
        raise ValueError(
            f"{abbreviation!r} is not a CVSS Base metric; "
            f"the eight are {', '.join(METRIC_ORDER)}"
        )
    return metric.name


def refuse_illegal_pair(name: str, value: str) -> None:
    """Refuse anything but a Base metric, or a value that metric forbids."""
    # Base only: a council answer or ruling is held to these.
    metric = METRICS_BY_ABBREVIATION.get(name)
    if metric is None:
        raise ValueError(
            f"Unknown metric {name!r}: this calculator reads the eight CVSS Base metrics only"
        )
    refuse_illegal_value(metric, value)


def refuse_unreadable_pair(name: str, value: str) -> None:
    """Refuse a metric a published vector may not carry, or a value that metric forbids."""
    metric = READABLE_METRICS.get(name)
    if metric is None:
        raise ValueError(unreadable_metric_message(name))
    refuse_illegal_value(metric, value)


def refuse_illegal_value(metric: Metric, value: str) -> None:
    """Refuse a value this metric does not allow, naming the ones it does."""
    if value in metric.values:
        return
    allowed = ", ".join(metric.values)
    raise ValueError(
        f"{value!r} is not a value of {metric.name} ({metric.abbreviation}); "
        f"allowed values are {allowed}"
    )


def unreadable_metric_message(name: str) -> str:
    """Say why a metric is refused: an Environmental one by name, anything else as unknown."""
    if name in ENVIRONMENTAL_METRICS:
        return (
            f"{name!r} is a CVSS Environmental metric, which this calculator does not read: "
            "it scores the Base, and the organisation's answers describe the environment"
        )
    return (
        f"Unknown metric {name!r}: this calculator reads the eight CVSS Base metrics and "
        "the three Temporal ones"
    )
