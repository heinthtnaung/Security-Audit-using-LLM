"""One published vector, split metric by metric, each with its name and value in a tooltip.

Split on its own separators, shown in published order, never recomputed. The differing metrics
are passed in from the record and marked `diff`. Names come from `cvss.metrics`.
"""

from cvss.metrics import READABLE_METRICS, VALUE_NAMES
from report.html_layout import tag, text

SLASH = '<span class="vs">/</span>'
VERSION_PREFIX = "CVSS"


def vector_markup(vector: str, differing: tuple[str, ...] = ()) -> str:
    """Render one vector as code, each metric a span with its tooltip, the differing ones marked."""
    fields = [field_span(one, differing) for one in vector.split("/")]
    return tag("code", SLASH.join(fields), "vector")


def field_span(field: str, differing: tuple[str, ...]) -> str:
    """Give one field of a vector: the version prefix, or a metric pair with its tooltip."""
    if field.startswith(VERSION_PREFIX):
        return tag("span", text(field), "vp")
    metric, _, value = field.partition(":")
    css = "vm diff" if metric in differing else "vm"
    return metric_span(field, css, tooltip(metric, value))


def metric_span(field: str, css: str, title: str) -> str:
    """Give one metric pair, with a title where the vocabulary names it, plain where it does not."""
    titled = f' title="{text(title)}"' if title else ""
    return f'<span class="{css}"{titled}>{text(field)}</span>'


def tooltip(metric: str, value: str) -> str:
    """Name one metric and its value, or nothing where the pair is not in the vocabulary."""
    known = READABLE_METRICS.get(metric)
    named_value = VALUE_NAMES.get(metric, {}).get(value)
    if known is None or named_value is None:
        return ""
    return f"{known.name}: {named_value}"
