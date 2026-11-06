"""Read a saved report's findings back into the records a run built from the scan.

The inverse of `report.json_report.finding_of`. The component and advisory are read straight
back; the scores are recomputed from the vectors through the real join, not read. `advisory.details`
is not in the record, so it is restored empty; `advisory.purl` is the component's join key.
"""

from typing import Any, Mapping

from deps.syft_report import Component
from deps.trivy_report import Advisory
from findings.finding import Finding, build_finding
from report.load_json import as_list, require, required_object


def finding_from(block: Mapping[str, Any], where: str) -> Finding:
    """Read one finding's component and advisory, and rebuild its scores through the real join."""
    component = component_from(required_object(block, "component", where))
    advisory_block = required_object(block, "advisory", where)
    advisory = advisory_from(advisory_block, component.purl, block, where)
    return build_finding(component, advisory)


def component_from(block: Mapping[str, Any]) -> Component:
    """Read one installed component back from the record."""
    return Component(
        name=str(require(block, "name", "component")),
        version=str(require(block, "version", "component")),
        purl=str(require(block, "purl", "component")),
        ecosystem=str(require(block, "ecosystem", "component")),
        locations=locations_from(block),
    )


def locations_from(block: Mapping[str, Any]) -> tuple[str, ...]:
    """Read the paths a component was found at, in the order the record keeps them."""
    return tuple(str(one) for one in as_list(require(block, "locations", "component"), "locations"))


def advisory_from(
    block: Mapping[str, Any], purl: str, finding: Mapping[str, Any], where: str
) -> Advisory:
    """Read one advisory back, restoring its vectors from the finding's two score lists."""
    return Advisory(
        advisory_id=str(require(block, "advisory_id", f"{where}.advisory")),
        purl=purl,
        fixed_version=none_or_str(block.get("fixed_version")),
        summary=str(require(block, "summary", f"{where}.advisory")),
        details="",
        vectors=vectors_from(finding, where),
        url=none_or_str(block.get("url")),
    )


def vectors_from(finding: Mapping[str, Any], where: str) -> dict[str, str]:
    """Rebuild every source's published vector, from the finding's scored and refused lists."""
    scored = as_list(require(finding, "scores", where), f"{where}.scores")
    refused = as_list(require(finding, "unreadable", where), f"{where}.unreadable")
    return dict(source_vector(one, where) for one in (*scored, *refused))


def source_vector(block: Mapping[str, Any], where: str) -> tuple[str, str]:
    """Read one source's name and the vector it published, as the record kept them."""
    at = f"{where}.vectors"
    return str(require(block, "source", at)), str(require(block, "vector", at))


def none_or_str(value: Any) -> str | None:
    """Read an optional string field, which the record writes as null when it has none."""
    return None if value is None else str(value)
