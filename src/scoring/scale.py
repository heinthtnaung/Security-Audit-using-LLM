"""The 0-100 scale a category score is measured on.

Both `CategoryScore` and `TechnicalSeverity` are bounded by it and summed together,
so there is one definition rather than two that could drift. It lives here, not in
`category.py`, because a technical severity is not a `CategoryScore`.
"""

MINIMUM_CATEGORY_SCORE = 0.0
MAXIMUM_CATEGORY_SCORE = 100.0
