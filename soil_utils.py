def drainage_class(dr_val: float | None) -> str:
    if dr_val is None or dr_val < 0:
        return ""

    # tabela em ordem crescente
    table = [
        ("Very Poorly",        0.01),
        ("Poorly",             0.05),
        ("Somewhat poorly",    0.25),
        ("Moderately well",    0.40),
        ("Well",               0.60),
        ("Somewhat excessive", 0.75),
        ("Excessive",          0.85),
        ("Very Excessive",     0.95),
    ]
    for label, val in table:
        if dr_val <= val + 1e-6:      # primeiro valor ≥ SLDR
            return label
    return "Very Excessive"           # SLDR maior que 0.95