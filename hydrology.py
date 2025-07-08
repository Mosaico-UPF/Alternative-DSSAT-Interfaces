# hydrology.py  --------------------------------------------------------
"""
Conversão entre % Slope × Curve Number (CN₂) tal como o utilitário
DSSAT **SBuild** faz internamente.

Declives-padrão por coluna:   1 % | 3 % | 8 % | 15 %

* :func:`slope_from_cn` devolve **sempre 1, 3, 8 ou 15** (sem interpolar).
* :func:`cn_from_slope` devolve o CN do limite superior da coluna em que
  o declive cai. É o valor que o SBuild gravaria se escolhesse
  esse declive na interface.
"""

from __future__ import annotations

from typing import Mapping, Sequence

# Limites de CN por grupo hidrológico (linhas) e por coluna (0-1-2-3)
HYDRO_TABLE: Mapping[str, tuple[int, int, int, int]] = {
    "Lowest":          (61, 73, 81, 84),   # Grupo A
    "Moderately Low":  (64, 76, 84, 87),   # Grupo B
    "Moderately High": (68, 80, 88, 91),   # Grupo C
    "Highest":         (71, 83, 91, 94),   # Grupo D
}

# Declives-representantes que o SBuild mostra em cada coluna
SLOPE_VALUES: Sequence[int] = (12, 8, 3, 1)        # ← 15 %, não 12 %

# ----------------------------------------------------------------------

def slope_from_cn(group: str, cn: int | float | str) -> int | None:
    """Converte *CN₂* em % Slope (1 / 3 / 8 / 15)."""
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
    return SLOPE_VALUES[-1]          # > último limite  → 15 %

# ----------------------------------------------------------------------

def cn_from_slope(group: str, slope_pct: float | int) -> int | None:
    """Devolve o CN do topo da coluna correspondente a *slope_pct*."""
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
