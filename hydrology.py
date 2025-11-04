# hydrology.py  --------------------------------------------------------
"""
Conversão entre % Slope × Curve Number (CN₂) tal como o utilitário
DSSAT **SBuild** faz internamente.

Declives-padrão por coluna (da esquerda para a direita na grade):

    1 % | 3 % | 8 % | 12 %

* :func:`slope_from_cn` devolve **sempre 1, 3, 8 ou 12** (sem interpolar).
* :func:`cn_from_slope` devolve o CN do limite superior da coluna em que
  o declive cai — é o valor que o SBuild gravaria se você escolhesse
  esse declive na interface.
"""

from __future__ import annotations
from typing import Mapping, Sequence

# Limites de CN por grupo hidrológico (linhas) e por coluna (0-1-2-3)
HYDRO_TABLE: Mapping[str, tuple[int, int, int, int]] = {
    "Lowest":           (63,   65,   73,   84),   # Grupo A
    "Moderately Low":   (68,   76,   84,   87),   # Grupo B
    "Moderately High":  (72, 85, 92, 96),   # Grupo C
    "Highest":          (75,   83,   91,   94),   # Grupo D
}

# Declives-representantes que o SBuild mostra em cada coluna
SLOPE_VALUES: Sequence[int] = (1, 3, 8, 12)

# ----------------------------------------------------------------------

def slope_from_cn(group: str, cn: int | float | str) -> int | None:
    row = HYDRO_TABLE.get(group)
    if row is None:
        return None
    try:
        cn_val = float(cn)
    except (TypeError, ValueError):
        return None

    if   cn_val <= row[0]: return 1    # 1 %
    elif cn_val <= row[1]: return 3    # 3 %
    elif cn_val <= row[2]: return 8    # 8 %
    else:                  return 12   # 12 %

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
