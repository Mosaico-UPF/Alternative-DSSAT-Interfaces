# hydrology.py  --------------------------------------------------------
"""

Conversion between % Slope x Curve Number (CN₂) 
DSSAT SBuild does internally

Standard Slope by column:   1 % | 3 % | 8 % | 15 %

* :func:`slope_from_cn` returns **always 1, 3, 8 or 15** (without interpolation).
* :func:`cn_from_slope` returns the CN of the upper limit of the row
  in which the slope falls — it's the value SBuild would save if you choose
  this slope in the UI.
"""
from __future__ import annotations

from typing import Mapping, Sequence

# CN Limits by hydrologic group(lines) and by row (0-1-2-3)
HYDRO_TABLE: Mapping[str, tuple[int, int, int, int]] = {
    "Lowest":          (61, 73, 81, 84),   # Group A
    "Moderately Low":  (64, 76, 84, 87),   # Group B
    "Moderately High": (68, 80, 88, 91),   # Group C
    "Highest":         (71, 83, 91, 94),   # Group D
}

# Representing Slope values that SBuild Displays in each column
SLOPE_VALUES: Sequence[int] = (12, 8, 3, 1)        # ← 15 %, not 12 %

# ----------------------------------------------------------------------

def slope_from_cn(group: str, cn: int | float | str) -> int | None:
    """Converts *CN₂* in % Slope (1 / 3 / 8 / 15)."""
    row = HYDRO_TABLE.get(group)
    if row is None:
        return None

    try:
        cn_val = float(cn)
    except (TypeError, ValueError):
        return None

    for slope, cn_lim in zip(SLOPE_VALUES, row):
        if cn_val <= cn_lim:
            return slope
    return SLOPE_VALUES[-1]          # > last limit  → 15 %

# ----------------------------------------------------------------------

def cn_from_slope(group: str, slope_pct: float | int) -> int | None:
    """Returns the CN to the top of the column correspondig to *slope_pct*."""
    row = HYDRO_TABLE.get(group)
    if row is None:
        return None
    try:
        slope = float(slope_pct)
    except (TypeError, ValueError):
        return None

    idx = (
        0 if slope <= 2 else
        1 if slope <= 5 else
        2 if slope <= 10 else
        3
    )
    return row[idx]

# ----------------------------------------------------------------------
__all__ = [
    "HYDRO_TABLE",
    "SLOPE_VALUES",
    "slope_from_cn",
    "cn_from_slope",
]
