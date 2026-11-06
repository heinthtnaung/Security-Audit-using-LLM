"""The version of the rules behind an Organisation Risk Score.

Two scores compare only if the same rules produced them: the questions and their
weights, the category weights, the clamp and CVSS scale, the band thresholds, the
floors, and what marks a score provisional. `SCORING_RULES_VERSION` names that set,
and every report carries it. Bump it whenever any of those changes.
"""

SCORING_RULES_VERSION = "ors-1"
