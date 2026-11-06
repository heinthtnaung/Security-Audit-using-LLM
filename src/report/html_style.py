"""The class that colours a severity band.

The colours themselves are tokens in `assets/*.css`. A CVSS chip and an Organisation Risk chip
never share a shape, so the band colour they share cannot make them read as one badge.
"""

from cvss.score import SEVERITY_BAND_NAMES

# The CVSS band names from `cvss.score`; they cover the organisation ones too.
BANDS: tuple[str, ...] = SEVERITY_BAND_NAMES

BAND_CLASSES = {name: f"band-{name.lower()}" for name in BANDS}


def band_class(band: str) -> str:
    """Give the class that colours one band, refusing a band the palette cannot reach."""
    named = BAND_CLASSES.get(band)
    if named is None:
        named_bands = ", ".join(BANDS)
        raise ValueError(f"{band!r} is no band this palette has a colour for: {named_bands}")
    return named
