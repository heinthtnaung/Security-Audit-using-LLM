"""The findings that need approval, on the terminal, each with the reasons the rule gives.

A block of their own, since a mark would not fit beside a one-line finding. Each reason is on
the line, so a flag can be traced to the rule.
"""

from report.approval_needed import NEEDS_APPROVAL, needing_approval, reasons_for
from report.record import Report
from report.text_layout import INDENT, SOURCE_SEPARATOR, id_width, identified, section


def approval_needed_block(report: Report) -> str:
    """List every finding the rule marks as needing approval, with the reasons it meets."""
    needing = needing_approval(report)
    if not needing:
        return ""
    width = id_width(needing)
    entries = [f"{INDENT}{identified(one, width)}  {reasons_line(report, one)}" for one in needing]
    return section(f"{NEEDS_APPROVAL.upper()} ({len(needing)})", entries)


def reasons_line(report: Report, finding) -> str:
    """Give the reasons one finding needs approval, side by side in the rule's order."""
    return SOURCE_SEPARATOR.join(reason.value for reason in reasons_for(report, finding))
