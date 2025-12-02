"""
Conversão entre % Slope × Curve Number (CN₂) conforme DSSAT SBuild.
"""

from __future__ import annotations
from typing import Mapping, Sequence

# Tabela CORRIGIDA conforme documentação oficial (Table 4)
HYDRO_TABLE: Mapping[str, tuple[int, int, int, int]] = {
    "Lowest":           (61, 64, 68, 71),
    "Moderately Low":   (73, 76, 80, 83),
    "Moderately High":  (81, 84, 88, 91),
    "Highest":          (84, 87, 91, 94),
}

SLOPE_VALUES: Sequence[int] = (1, 3, 8, 12)

# ----------------------------------------------------------------------

def cn_to_group(cn: int | float | str) -> str:
    """
    Retorna o grupo hidrológico baseado no CN.
    
    Args:
        cn: Curve Number (61-94)
        
    Returns:
        str: "Lowest", "Moderately Low", "Moderately High" ou "Highest"
             ou string vazia se inválido
    
    Examples:
        >>> cn_to_group(66)
        'Lowest'
        >>> cn_to_group(75)
        'Moderately Low'
        >>> cn_to_group(85)
        'Moderately High'
        >>> cn_to_group(92)
        'Highest'
    """
    try:
        cn_val = float(cn)
    except (TypeError, ValueError):
        return ""
    
    # Limites baseados nos valores MÍNIMOS de cada grupo na tabela
    if cn_val <= 71:           # Grupo A (61-71)
        return "Lowest"
    elif cn_val <= 83:         # Grupo B (73-83)
        return "Moderately Low"
    elif cn_val <= 91:         # Grupo C (81-91)
        return "Moderately High"
    else:                      # Grupo D (84-94)
        return "Highest"

# ----------------------------------------------------------------------

def slope_from_cn(group: str, cn: int | float | str) -> int | None:
    """
    Retorna o % Slope representativo (1, 3, 8 ou 12) baseado no CN e grupo.
    
    Args:
        group: "Lowest", "Moderately Low", "Moderately High" ou "Highest"
        cn: Curve Number (61-94)
        
    Returns:
        int: 1, 3, 8 ou 12 (%) ou None se inválido
    """
    row = HYDRO_TABLE.get(group)
    if row is None:
        return None
    
    try:
        cn_val = float(cn)
    except (TypeError, ValueError):
        return None

    # Compara CN com os limites da tabela
    if   cn_val <= row[0]: return 1    # 0-2%   → 1%
    elif cn_val <= row[1]: return 3    # 2-5%   → 3%
    elif cn_val <= row[2]: return 8    # 5-10%  → 8%
    else:                  return 12   # >10%   → 12%

# ----------------------------------------------------------------------

def cn_from_slope(group: str, slope_pct: float | int) -> int | None:
    """
    Retorna o CN correspondente ao slope informado.
    
    Args:
        group: Grupo hidrológico
        slope_pct: Declividade em %
        
    Returns:
        int: Curve Number correspondente
    """
    row = HYDRO_TABLE.get(group)
    if row is None:
        return None
    
    try:
        slope = float(slope_pct)
    except (TypeError, ValueError):
        return None

    # Mapeia slope para coluna conforme documentação
    if   slope <= 2:   idx = 0  # 0-2%
    elif slope <= 5:   idx = 1  # 2-5%
    elif slope <= 10:  idx = 2  # 5-10%
    else:              idx = 3  # >10%
    
    return row[idx]

# ----------------------------------------------------------------------
__all__ = [
    "HYDRO_TABLE",
    "SLOPE_VALUES",
    "cn_to_group",
    "slope_from_cn",
    "cn_from_slope",
]