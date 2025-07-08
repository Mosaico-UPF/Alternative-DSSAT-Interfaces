def calculateMissingValues(self) -> None:
    tw = self.tableCalc
    n_rows = tw.rowCount()

    # 1)  percorre linha a linha 
    for r in range(n_rows):
        # Leitura segura das entradas já digitadas
        def f(col) -> float | None:
            item = tw.item(r, col)
            if not item:
                return None
            try:
                v = float(item.text())
                return None if v == -99 else v
            except Exception:
                return None

        depth = f(0)   # só para referência - não será calculado
        clay  = f(1)
        silt  = f(2)
        stones= f(3)

        # Lower limit (θLL / SLLL) 
        lll = f(4)
        if lll is None:
            # TODO: exemplo de pedotransfer simples
            # lll = 0.1 + 0.003 * clay
            if clay is not None:
                lll = max(0, 0.1 + 0.003 * clay)
                tw.setItem(r, 4, QTableWidgetItem(f"{lll:.3f}"))

        # Drained upper limit (θDUL / SDUL)
        dul = f(5)
        if dul is None and lll is not None:
            # TODO: regra provisória
            # dul = lll + 0.08
            dul = lll + 0.08
            tw.setItem(r, 5, QTableWidgetItem(f"{dul:.3f}"))

        # Saturated water content (θSAT / SSAT)
        sat = f(6)
        if sat is None and dul is not None:
            # TODO: valor típico
            sat = dul + 0.10
            tw.setItem(r, 6, QTableWidgetItem(f"{sat:.3f}"))

        # Bulk density (SBDM) 
        bd = f(7)
        if bd is None and sat is not None:
            # ρb ≈ (1 - θSAT) * 2.65 g cm⁻³
            bd = (1 - sat) * 2.65
            tw.setItem(r, 7, QTableWidgetItem(f"{bd:.2f}"))

        # Saturated hydraulic conductivity (SSKS) 
        ksat = f(8)
        if ksat is None and clay is not None and sat is not None:
            ksat = 10 ** (-0.6 + 1.3 * (1 - clay/100))
            tw.setItem(r, 8, QTableWidgetItem(f"{ksat:.2f}"))

        # Root-growth factor (SRGF) 
        rgf = f(9)
        if rgf is None and depth is not None:
            # fator decrescente linear até 200 cm
            rgf = max(0, 1 - depth / 200)
            tw.setItem(r, 9, QTableWidgetItem(f"{rgf:.3f}"))
