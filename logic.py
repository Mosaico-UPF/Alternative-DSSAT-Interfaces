import sys
import tempfile
from PyQt5.QtGui import QColor
import os
from typing import Optional
from pathlib import Path
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import (
    QFileDialog,
    QMessageBox,
    QComboBox,
    QDialog,
    QTableWidgetItem
)
from PyQt5.QtCore import Qt
import math
from sbuild import Ui_MainWindow
from profileList import Ui_Dialog, ProfileListDialog
from readSoilFile import read_profile, show_profiles
from createSoilFile import build_soil_file
from updateSoilFile import update_soil_file
from deleteSoilFile import delete_soil_profile
from hydrology import slope_from_cn

def runoff_group(cn: float) -> str:
    if cn <= 70:
        return "Lowest"              # Grupo A
    elif cn <= 80:
        return "Moderately Low"      # Grupo B
    elif cn <= 90:
        return "Moderately High"     # Grupo C
    else:
        return "Highest"             # Grupo D

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

class MainWindow(QtWidgets.QMainWindow):
    
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.currentSolFile = None
        self._pendingSave = None
        self.currentProfile: Optional[dict] = None
        self.ui.buttonBox.accepted.connect(self.handlePage0Ok)
        self.ui.buttonBox.rejected.connect(self.handlePage0Cancel)
        self.ui.buttonBox_3.accepted.connect(self.goToFinalPage)
        self.ui.buttonBox_3.rejected.connect(self.goBack)
        self.ui.buttonBox_2.accepted.connect(self.goBack)
        self.ui.buttonBox_2.rejected.connect(self.goBack)
        self.ui.finish.accepted.connect(self.handlePage3Ok)
        self.ui.finish.rejected.connect(self.goToPage2)
        self.ui.pushButton_2.clicked.connect(self.goForward)
        self.ui.pushButton_3.clicked.connect(self.addLayer)
        self.ui.pushButton_4.clicked.connect(self.deleteLayer)
        self.ui.actionClose_3.triggered.connect(self.closeProfile)
        self.ui.pushButton.clicked.connect(self.calculateMissingValues)
        self.ui.tableWidget.setSortingEnabled(False)
        self.tableCalc = self.ui.tableWidget_3
        self.ui.pushButton_4.setEnabled(False)
        # dispara sempre que o usuário muda de página no wizard
        self.ui.actionOpen.triggered.connect(self.openSolFile)
        self.ui.actionClose_2.triggered.connect(self.closeSolFile)
        self.ui.actionEdit_3.triggered.disconnect()
        self.ui.actionSave_2.triggered.connect(self.writeSolFile)
        self.ui.actionEdit_3.triggered.connect(self.openProfileList)
        self.ui.actionDelete_3.triggered.connect(self.askDeleteProfile)
        self.ui.actionExit.triggered.connect(self.handlePage0Cancel)
        self.ui.actionNew_3.triggered.connect(self.newSolFile)
        self.ui.stackedWidget.currentChanged.connect(self._on_page_changed)
        self._prepare_combo(self.ui.color_box)
        self._prepare_combo(self.ui.drainage_box)
        self._prepare_combo(self.ui.runoffPotential_box)
        # Inside your MainWindow __init__, after setupUi(...)
        self.fileStatusAction = QtWidgets.QAction("", self)
        self.fileStatusAction.setEnabled(False)
        mb = self.menuBar()
        assert mb is not None, "menuBar não inicializado"
        mb.addAction(self.fileStatusAction)
        mb.setStyleSheet("QMenuBar::item:disabled { color: black; }")

    def addLayer(self) -> None:
        """Adiciona uma nova camada (+ 5 cm) sincronizando TODAS as grades."""
        tw1 = self.ui.tableWidget          # grade principal
        tw2 = self.ui.tableWidget_2        # “More inputs”
        tw3 = self.tableCalc               # “Calculate/Edit Soil Parameters”
        r   = tw1.rowCount()               # índice da nova linha

        # ── profundidade -------------------------------------------------------
        if r == 0:
            depth_val = 5
        else:
            try:
                depth_val = int(tw1.item(r - 1, 0).text()) + 5
            except Exception:
                depth_val = 5

        # ── insere linha nas três tabelas -------------------------------------
        for tw in (tw1, tw2, tw3):
            tw.insertRow(r)
            tw.setItem(r, 0, QTableWidgetItem(str(depth_val)))

        # coluna “Master horizon” (grade principal) com default –99
        tw1.setItem(r, 1, QTableWidgetItem("-99"))

        self.checkButton()

    def preview(self):
        # implementar
        pass

    def closeSolFile(self) -> None:
        """Fecha o .SOL em uso (se houver) após confirmação
        e limpa toda a interface."""
        if not self.currentSolFile:
            return                               # nenhum arquivo aberto

        if QMessageBox.question(
            self,
            "Close file",
            "Are you sure you want to close this file?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        ) != QMessageBox.Yes:
            return                               # cancelado

        # ── zera variáveis de estado ────────────────────────────────
        self.currentSolFile = None
        self.currentProfile = None
        self.fileStatusAction.setText("")

        # ── limpa campos “General Information” ──────────────────────
        self.cleanFields()

        # ── limpa superfície (aba Page 1) ───────────────────────────
        self.ui.color_box.setCurrentIndex(-1)
        self.ui.drainage_box.setCurrentIndex(-1)
        self.ui.runoffPotential_box.setCurrentIndex(-1)
        self.ui.slope_line.clear()
        self.ui.fertilityFactor_line.clear()

        # ── limpa campos da aba “Calculate/Edit” ────────────────────
        self.ui.lineEdit.clear()      # Runoff Curve Number
        self.ui.lineEdit_2.clear()    # Albedo
        self.ui.lineEdit_3.clear()    # Drainage Rate

        # ── limpa as três tabelas de camadas ────────────────────────
        for tw in (self.ui.tableWidget,
                   self.ui.tableWidget_2,
                   self.tableCalc):
            tw.setRowCount(0)

        self.checkButton()            # atualiza estado do botão “Delete”

    def newSolFile(self) -> None:
        if not self.currentSolFile:
            return                               # nenhum arquivo aberto

        if QMessageBox.question(
            self,
            "New file",
            "Are you sure you want to create a new file?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        ) != QMessageBox.Yes:
            return                               # cancelado

        # ── zera variáveis de estado ────────────────────────────────
        self.currentSolFile = None
        self.currentProfile = None
        self.fileStatusAction.setText("")

        # ── limpa campos “General Information” ──────────────────────
        self.cleanFields()

        # ── limpa superfície (aba Page 1) ───────────────────────────
        self.ui.color_box.setCurrentIndex(-1)
        self.ui.drainage_box.setCurrentIndex(-1)
        self.ui.runoffPotential_box.setCurrentIndex(-1)
        self.ui.slope_line.clear()
        self.ui.fertilityFactor_line.clear()

        # ── limpa campos da aba “Calculate/Edit” ────────────────────
        self.ui.lineEdit.clear()      # Runoff Curve Number
        self.ui.lineEdit_2.clear()    # Albedo
        self.ui.lineEdit_3.clear()    # Drainage Rate

        # ── limpa as três tabelas de camadas ────────────────────────
        for tw in (self.ui.tableWidget,
                   self.ui.tableWidget_2,
                   self.tableCalc):
            tw.setRowCount(0)

        self.checkButton()            # atualiza estado do botão “Delete”

    def cleanFields(self):
        self.ui.country_line.clear()
        self.ui.instituteCode_line.clear()
        self.ui.siteName_line.clear()
        self.ui.latitude_line.clear()
        self.ui.longitude_line.clear()
        self.ui.soilSeries_line.clear()
        self.ui.soilData_line.clear()
        self.ui.soilClassification_line.clear()

    def populateFieldsFromProfile(self, profile: dict) -> None:
        # ─── caminho do .SOL + código ─────────────────────────────────
        sol0 = self.getCurrentSolFile()
        if sol0 is None:
            QMessageBox.warning(self, "Warning", "No .SOL file opened.")
            return
        sol: str = sol0
        code = profile["code"]
        data = read_profile(sol, code)

        # === General Information =====================================
        self.ui.country_line.setText(data["country"])
        self.ui.siteName_line.setText(data["site_name"])
        self.ui.instituteCode_line.setText(data["institute_code"])
        self.ui.latitude_line.setText(data["latitude"])
        self.ui.longitude_line.setText(data["longitude"])
        self.ui.soilData_line.setText(data["soil_data_source"])
        self.ui.soilSeries_line.setText(data["soil_series_name"])
        self.ui.soilClassification_line.setText(data["soil_classification"])

        # === Surface Information =====================================
        cmap = {
            "BL": "Black", "BK": "Black",
            "BN": "Brown", "BR": "Brown",
            "G":  "Grey",  "GY": "Grey",
            "R":  "Red",   "RD": "Red",
            "Y":  "Yellow","YL": "Yellow",
        }

        # --- Color ----------------------------------------------------
        code_color = (data.get("color_code") or "").strip().upper()
        if code_color and cmap.get(code_color):
            self.ui.color_box.setCurrentText(cmap[code_color])
        else:
            # nulo ou código desconhecido → não selecionar nada
            self.ui.color_box.setCurrentIndex(-1)

        # Drainage class (combo) --------------------------------------
        try:
            dr_val = float(data["drainage_rate"])
        except (TypeError, ValueError):
            dr_val = None

        label = drainage_class(dr_val)
        
        if label:
            self.ui.drainage_box.setCurrentText(label)
        else:
            self.ui.drainage_box.setCurrentIndex(-1)

        # Run-off potential & % slope ---------------------------------
        slope_txt = (data.get("slope")
                     or data.get("%slope")
                     or data.get("slope_percent")
                     or "").strip()
        try:
            rc = float(data["runoff_curve"] or 0)
        except ValueError:
            rc = 0.0
        
        if slope_txt != "":
            self.ui.slope_line.setText(slope_txt)

            if rc > 0:
                self.ui.runoffPotential_box.setCurrentText(runoff_group(rc))
            else:
                self.ui.runoffPotential_box.setCurrentIndex(-1)
        
        else:
            if rc > 0:
                txt_ro = runoff_group(rc)
                self.ui.runoffPotential_box.setCurrentText(txt_ro)
                slope_val = slope_from_cn(txt_ro, int(rc))
                self.ui.slope_line.setText("" if slope_val is None else str(slope_val))
            else:
                self.ui.runoffPotential_box.setCurrentIndex(-1)
                self.ui.slope_line.clear()

        ff = data.get("fertility_factor")
        self.ui.fertilityFactor_line.setText("" if ff in (None, "", "-99") else str(ff))

        # === Surface-parameter widgets na aba “Calculate/Edit” =======
        # ajuste os nomes se seus QLineEdits forem diferentes
        rc_val = data.get("runoff_curve")
        self.ui.lineEdit.setText("" if rc_val in (None, "", "-99") else str(rc_val))  # SLRO
        salb_val = data.get("albedo")
        self.ui.lineEdit_2.setText("" if salb_val in (None, "", "-99") else str(salb_val))  # SALB
        sldr_val = data.get("drainage_rate")
        self.ui.lineEdit_3.setText("" if sldr_val in (None, "", "-99") else str(sldr_val))  # SLDR

        # === Layers tables (principal + more-inputs + calculate) =====
        tw_main = self.ui.tableWidget
        tw_more = self.ui.tableWidget_2
        tw_calc = self.tableCalc          # grade da aba “Calculate/Edit”

        # limpa todas
        for tw in (tw_main, tw_more, tw_calc):
            tw.setRowCount(0)

        # ordem exata das colunas de cada grade -----------------------
        main_keys = ["depth", "texture", "clay", "silt",
                    "stones", "oc", "ph", "cec", "tn"]

        # grade de cálculo – todas as colunas já existentes no .ui
        calc_keys = ["depth", "clay", "silt", "stones",
                    "lll", "dul", "sat", "bd", "ksat", "srgf"]

        for layer in data.get("layers", []):
            r = tw_main.rowCount()

            # cria linha nas três grades
            for tw in (tw_main, tw_more, tw_calc):
                tw.insertRow(r)

            # ── grade principal ---------------------------------------
            for c, k in enumerate(main_keys):
                tw_main.setItem(r, c, QTableWidgetItem(layer.get(k, "")))

            # ── more-inputs: apenas profundidade (espelhada) ----------
            tw_more.setItem(r, 0, QTableWidgetItem(layer.get("depth", "")))

            # ── grade de cálculo (todos os parâmetros) ----------------
            for c, k in enumerate(calc_keys):
                tw_calc.setItem(r, c, QTableWidgetItem(layer.get(k, "")))

        self.checkButton()

    def openSolFile(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Abrir arquivo .SOL para leitura de perfis",
            "",
            "Arquivos DSSAT (*.SOL);;Todos os arquivos (*)",
            options=options
        )
        if file_name:
            self.setCurrentSolFile(file_name)
            self.fileStatusAction.setText(os.path.basename(file_name))
        if not file_name:
            return  # Usuário cancelou
        else: 
            self.setCurrentSolFile(file_name)
        try:
            # Chama show_profiles para extrair os perfis do arquivo selecionado
            profiles = show_profiles(file_name)  # Retorna uma lista de dicionários

            if profiles:
                # Extrai o código de cada perfil para exibição
                message = "\n\n".join(
                f"Perfil: {profile['code']}\n{profile['content']}" for profile in profiles
            )
                #QMessageBox.information(self, "Perfis de Solo", f"Perfis encontrados:\n{message}")
            else:
                QMessageBox.information(self, "Perfis de Solo", "Nenhum perfil encontrado no arquivo.")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao ler o arquivo:\n{e}")
    
    def setCurrentSolFile(self, file_name: str):
        self.currentSolFile = file_name
        full_path = os.path.abspath(file_name)
        self.fileStatusAction.setText(f"Working with file {full_path}")

    # ──────────────────────────────────────────────────────────────────────
    def closeProfile(self) -> None:
        """
        Resets the UI back to the “no-profile-selected” state **without**
        closing the .SOL file itself.
        """
        if self.currentProfile is None:
            return  # nothing to do

        # 1. forget the selection
        self.currentProfile = None

        # 2. clear General-Information fields
        self.cleanFields()

        # 3. reset surface widgets (Page 1)
        self.ui.color_box.setCurrentIndex(-1)
        self.ui.drainage_box.setCurrentIndex(-1)
        self.ui.runoffPotential_box.setCurrentIndex(-1)
        self.ui.slope_line.clear()
        self.ui.fertilityFactor_line.clear()

        # 4. reset Calculate/Edit widgets (Page 2)
        self.ui.lineEdit.clear()      # SLRO
        self.ui.lineEdit_2.clear()    # SALB
        self.ui.lineEdit_3.clear()    # SLDR

        # 5. wipe the three layer tables
        for tw in (self.ui.tableWidget,
                self.ui.tableWidget_2,
                self.tableCalc):
            tw.setRowCount(0)

        # 6. update buttons that depend on row count
        self.checkButton()
    # ──────────────────────────────────────────────────────────────────────


    def getCurrentSolFile(self) -> Optional[str]:
        return self.currentSolFile
    
    # ↓ cole dentro da classe MainWindow (fora de qualquer outro método) ─────
# -----------------------------------------------------------------------
    def _collect_layers(self) -> list[dict]:
        """Lê TODAS as linhas da grade principal e devolve [{SLB, SLLL, …}, …]."""
        tw_main = self.ui.tableWidget
        tw_calc = self.tableCalc

        layers: list[dict] = []
        for r in range(tw_main.rowCount()):
            try:  # profundidade é obrigatória
                slb = int(tw_main.item(r, 0).text())
            except Exception:
                continue     # pula linhas vazias

            layer = {
                # básicos (grade principal) -------------------------------
                "slb":  slb,
                "slmh":   tw_main.item(r, 1).text()  if tw_main.item(r, 1)  else "-99",
                "slcl":   tw_main.item(r, 2).text()  if tw_main.item(r, 2)  else -99,
                "slsi":   tw_main.item(r, 3).text()  if tw_main.item(r, 3)  else -99,
                "slcf":   tw_main.item(r, 4).text()  if tw_main.item(r, 4)  else -99,
                "sloc":   tw_main.item(r, 5).text()  if tw_main.item(r, 5)  else -99,
                "slhw":   tw_main.item(r, 6).text()  if tw_main.item(r, 6)  else -99,
                "scec":   tw_main.item(r, 7).text()  if tw_main.item(r, 7)  else -99,
                "slni":   tw_main.item(r, 8).text()  if tw_main.item(r, 8)  else -99,
                # hidráulicos (grade cálculo) ----------------------------
                "slll":   tw_calc.item(r, 4).text()  if tw_calc.item(r, 4)  else -99,
                "sdul":   tw_calc.item(r, 5).text()  if tw_calc.item(r, 5)  else -99,
                "ssat":   tw_calc.item(r, 6).text()  if tw_calc.item(r, 6)  else -99,
                "sbdm":   tw_calc.item(r, 7).text()  if tw_calc.item(r, 7)  else -99,
                "ssks":   tw_calc.item(r, 8).text()  if tw_calc.item(r, 8)  else -99,
                "srgf":   tw_calc.item(r, 9).text()  if tw_calc.item(r, 9)  else -99,
            }
            layers.append(layer)
        return layers
    # -----------------------------------------------------------------------

    def _sync_calc_from_main(self) -> None:
        """
        Copia Depth, Clay, Silt e Stones da grade principal
        para a grade Calculate/Edit, mantendo as linhas alinhadas.
        Só é chamada quando estamos criando um NOVO perfil.
        """
        tw_main = self.ui.tableWidget      # grade “Input table”
        tw_calc = self.tableCalc           # grade “Calculate/Edit”

        rows = tw_main.rowCount()
        tw_calc.setRowCount(rows)          # garante mesmo nº de linhas

        for r in range(rows):
            # (coluna na grade principal → coluna na grade calc)
            mapping = {
                0: 0,   # Depth → Depth
                2: 1,   # Clay  → Clay
                3: 2,   # Silt  → Silt
                4: 3,   # Stones→ Stones
            }
            for src_col, dst_col in mapping.items():
                src_item = tw_main.item(r, src_col)
                if src_item:
                    tw_calc.setItem(r, dst_col,
                                    QTableWidgetItem(src_item.text()))
    # ---------------------------------------------------------------

    _CALC_PAGE_INDEX = 3          # 2 se a aba “Calculate/Edit” for a 3ª página;
                                # 3 se for a 4ª (parece ser 2 pelo seu .ui)

    def _on_page_changed(self, idx: int) -> None:
        """
        Copia Depth, Clay, Silt e Stones do Input-Table para a grade
        Calculate/Edit assim que a aba é exibida **somente**
        quando estamos criando um perfil novo (nenhum .SOL aberto e
        self.currentProfile == None).
        """
        if idx != self._CALC_PAGE_INDEX:               # não é a página alvo
            return
        if self.currentProfile is not None:            # perfil carregado? não copia
            return
        if any(self.tableCalc.item(r, 0) for r in range(self.tableCalc.rowCount())):
            return                                     # grade cálculo já preenchida
        self._sync_calc_from_main()                    # faz o espelhamento

    def _write_profile(self, profile_id: str, sol_path: Optional[Path]) -> None:
        """
        Decide entre criar novo arquivo, anexar novo perfil ou atualizar perfil
        existente, de acordo com o estado atual da UI.
        """
        def _f(txt, default):
            try: return float((txt or "").strip())
            except Exception: return default

        layers = self._collect_layers()
        if not layers:
            raise ValueError("Tabela de camadas vazia.")

        # --- cabeçalho ---------------------------------------------------
        kwargs = dict(
            profile_id          = profile_id,
            site                = self.ui.siteName_line.text()         or "-99",
            country             = self.ui.country_line.text()          or "-99",
            lat                 = float(self.ui.latitude_line.text() or 0),
            lon                 = float(self.ui.longitude_line.text() or 0),
            layers              = layers,
            salb                = float(self.ui.lineEdit_2.text() or 0.13),
            sldr                = float(self.ui.lineEdit_3.text() or 0.6),
            slro                = float(self.ui.lineEdit.text()  or 61),
            slpf       = _f(self.ui.fertilityFactor_line.text(), 1.00),
            soil_data_source    = self.ui.soilData_line.text()         or "-99",
            soil_series_name    = self.ui.soilSeries_line.text()       or "-99",
            scs_family          = self.ui.soilClassification_line.text() or "-99",
            scom                = {"Black":"BL","Brown":"BN","Grey":"G",
                                "Red":"R","Yellow":"Y"}.get((self.ui.color_box.currentText() or "").strip(), ""),
        )

        if sol_path is None:             # 1) novo arquivo
            dest = QFileDialog.getSaveFileName(self,
                                            "Salvar novo arquivo .SOL",
                                            f"{profile_id}.SOL",
                                            "Arquivos DSSAT (*.SOL)")[0]
            if not dest:  # cancelado
                return
            build_soil_file(dest=dest, **kwargs)

        elif self.currentProfile is None:          # 2) append a novo perfil
            # --- cria arquivo-temporário REALMENTE provisório -------------
            with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".SOL", mode="w", encoding="utf-8") as tf:
                tmp_path = Path(tf.name)

            build_soil_file(dest=tmp_path, **kwargs)   # gera bloco sozinho

            # carrega o bloco recém-criado (descarta cabeçalhos de arquivo)
            new_block = "\n".join(
                tmp_path.read_text(encoding="utf-8").splitlines()[2:]
            )
            tmp_path.unlink()                          # remove o temporário

            # --- anexa ao .SOL original -------------------------------------------------
            # garante \n antes/depois para nunca “colar” perfis
            # -- anexa ao .SOL original -----------------------------------------
            with open(sol_path, "r+", encoding="utf-8") as f:
                content = f.read()

                # prefixo que garante SEMPRE uma linha vazia de separação
                if content.endswith("\n"):
                    prefix = "\n"          # já havia \n final  → adiciona mais 1
                else:
                    prefix = "\n\n"        # faltava \n final  → fecha e cria a vazia

                if not new_block.endswith("\n"):
                    new_block += "\n"

                # grava depois do EOF
                f.seek(0, os.SEEK_END)
                f.write(prefix + new_block)

    # -----------------------------------------------------------------------
        
    def openProfileList(self):
        sol = self.getCurrentSolFile()
        if not sol or not Path(sol).exists():
            QMessageBox.warning(self, "Warning", "No .SOL file opened.")
            return

        profiles = show_profiles(sol)
        dlg = ProfileListDialog(profiles, self)
        if dlg.exec_() == QDialog.Accepted and dlg.selected_profile:
            self.currentProfile = dlg.selected_profile
            assert self.currentProfile is not None, "Select a profile first"
            self.populateFieldsFromProfile(self.currentProfile)

    def calculateMissingValues(self) -> None:
        """
        Replica o botão “Calculate missing values” do SBuild
        (versão resumida -- apenas θLL, θDUL, θSAT, BD, Ksat, SRGF).

        Requer que % argila e % silte estejam presentes em TODAS as camadas.
        """
        tw = self.tableCalc
        n   = tw.rowCount()

        BLUE = QColor(200, 225, 255)       # marca visual p/ novos valores

        def num(r: int, c: int) -> float | None:
            """Lê um float da célula (None se vazia ou –99)."""
            item = tw.item(r, c)
            if not item:                    return None
            try:
                v = float(item.text())
                return None if v == -99 else v
            except Exception:
                return None

        def put(r: int, c: int, value: float, fmt: str = ".3f") -> None:
            """Escreve na célula e pinta de azul se antes estava vazia."""
            if tw.item(r, c):               # já existia → não muda
                return
            item = QTableWidgetItem(format(value, fmt))
            item.setBackground(BLUE)
            tw.setItem(r, c, item)

        # ── loop camada a camada ─────────────────────────────────────────
        for r in range(n):
            depth = num(r, 0)              # centro da layer (cm) – opcional
            clay  = num(r, 1)
            silt  = num(r, 2)
            sand  = None if None in (clay, silt) else max(0, 100 - clay - silt)
            om    = 1.72 * num(r, 5) if num(r, 5) is not None else 0  # %MO≈1.72×%C

            if None in (clay, silt):
                QMessageBox.warning(self, "Missing texture",
                                    "Each layer needs % clay and % silt "
                                    "before running this calculation.")
                return

            # Saxton & Rawls (2006) – θ à 1500 kPa (LL) e 33 kPa (DUL)
            if sand is not None:
                # coefs pequenos arredondados
                θ1500 = (-0.024*sand) + (0.487*clay) + (0.006*om) \
                        + (0.005*sand*om) - (0.013*clay*om) + 0.068
                θ33   = (-0.251*sand) + (0.195*clay) + (0.011*om) \
                        + (0.006*sand*om) - (0.027*clay*om) + 0.492

                put(r, 4, max(0, θ1500/100))        # LL – coluna 4
                put(r, 5, max(0, θ33  /100))        # DUL – coluna 5

            # θSAT = 1 – ρb/2.65   (bd em g cm-3)
            bd = num(r, 7)
            if bd is None:
                # Rawls (1983) bulk density
                bd = 1.636 - 0.005*clay - 0.043*om
                put(r, 7, bd, ".2f")

            sat = num(r, 6)
            if sat is None and bd is not None:
                sat = max(0, 1 - bd/2.65)
                put(r, 6, sat)

            # Ksat – Rawls & Brakensiek (1985) simplificado
            ksat = num(r, 8)
            if ksat is None and None not in (clay, silt, bd):
                log10K = 2.0 - 0.6*(clay/100) - 1.0*(silt/100) - 3.0*(bd/2.65)
                ksat = 10 ** log10K          # cm h-1
                put(r, 8, ksat, ".1f")

            # SRGF tradicional: exp(-0.02·z)
            rgf = num(r, 9)
            if rgf is None and depth is not None:
                put(r, 9, max(0, math.exp(-0.02*depth)))

        # ── SALB, SWCON, CN2 podem ficar para outra rotina (uma vez / perfil) ──
        QMessageBox.information(self, "Done",
                                "Missing hydraulic values calculated.")

    def writeSolFile(self) -> None:
        # ── arquivo aberto? ───────────────────────────────────────────
        sol = self.getCurrentSolFile()
        if not sol or not Path(sol).exists():
            QMessageBox.warning(self, "Warning",
                                "No .SOL file opened for editing.")
            return

        # ── sempre precisamos das camadas digitadas ───────────────────
        layers = self._collect_layers()
        if not layers:
            QMessageBox.warning(self, "Error",
                                "Add at least one soil layer before saving.")
            return

        # ------------------------------------------------------------------
        # A) PERFIL SELECIONADO  →  atualizar bloco existente
        # ------------------------------------------------------------------
        if self.currentProfile:
            def _f_or_none(txt):
                t = (txt or "").strip()
                if t == "": return None
                try: return float(t)
                except Exception: return None

            code = self.currentProfile["code"]

            # trecho da sua writeSolFile  (ramo: perfil selecionado)
            updates = {
                "site":      self.ui.siteName_line.text()  or "-99",
                "country":   self.ui.country_line.text()   or "-99",

                # 👇  acrescente tudo o que deseja gravar
                "lat":  float(self.ui.latitude_line.text()  or 0),
                "long": float(self.ui.longitude_line.text() or 0),
                "scom": {"Black":"BL","Brown":"BN","Grey":"G","Red":"R","Yellow":"Y"}.get((self.ui.color_box.currentText() or "").strip(), ""),

                "soil_series_name": self.ui.soilSeries_line.text(),
                "scs_family":       self.ui.soilClassification_line.text(),
                "salb": float(self.ui.lineEdit_2.text() or 0.13),
                "sldr": float(self.ui.lineEdit_3.text() or 0.60),
                "slro": float(self.ui.lineEdit.text()  or 61),

                # idem se quiser salvar *soil_data_source*, *scom*, etc.
                # "soil_data_source": self.ui.soilData_line.text() or "-99",

                "layers": layers,          # mantém as camadas
            }

            try:
                update_soil_file(sol, code, updates)
                QMessageBox.information(self, "OK",
                    f"Soil profile «{code}» updated successfully in «{sol}».")
            except Exception as e:
                QMessageBox.critical(self, "Error",
                                    f"Failed to save:\n{e}")
            return  # nada mais a fazer

        # ------------------------------------------------------------------
        # B) NENHUM perfil selecionado  →  criar NOVO bloco e anexar
        # ------------------------------------------------------------------
        pid, ok = QtWidgets.QInputDialog.getText(
            self, "New profile ID",
            "Enter the new profile code (exactly 10 characters):")
        if not ok:
            return
        pid = pid.strip().upper()
        if len(pid) != 10:
            QMessageBox.warning(self, "Error",
                                "Profile code must be exactly 10 characters.")
            return

        try:
            # _write_profile() extrai todos os campos da UI
            # e, como self.currentProfile é None, faz o append correto.
            self._write_profile(pid, Path(sol))
            QMessageBox.information(self, "OK",
                f"New soil profile «{pid}» added to «{sol}».")
        except Exception as e:
            QMessageBox.critical(self, "Error",
                                f"Failed to save:\n{e}")

    # ---------------------------------------------------------------
    def askDeleteProfile(self):                                     # ADD
        """Abre a lista de perfis, pergunta qual excluir e faz a remoção."""
        sol = self.getCurrentSolFile()
        if not sol or not Path(sol).exists():
            QMessageBox.warning(self, "Warning", "No .SOL file opened.")
            return

        profiles = show_profiles(sol)
        if not profiles:
            QMessageBox.information(self, "Warning", "No profiles found")
            return

        # mesmo diálogo usado em editar
        dlg = ProfileListDialog(profiles, self)
        dlg.setWindowTitle("Choose the profile to delete")
        if dlg.exec_() != QDialog.Accepted or not dlg.selected_profile:
            return

        code = dlg.selected_profile["code"]
        if QMessageBox.question(
                self,
                "Confirm Exclusion",
                f"Remove profile '{code}' from {os.path.basename(sol)}?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No) != QMessageBox.Yes:
            return

        try:
            delete_soil_profile(sol, code)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete profile:\n{e}")
            return

        # limpa UI se o perfil exibido era o apagado
        if self.currentProfile and self.currentProfile.get("code") == code:
            self.currentProfile = None
            self.cleanFields()

        QMessageBox.information(self, "OK", f"Profile '{code}' deleted.")
    # ---------------------------------------------------------------

    def _prepare_combo(self, combo: QComboBox):
        combo.setEditable(False)       
        combo.setInsertPolicy(QComboBox.NoInsert)   
        combo.setCurrentIndex(-1)       # nenhum item selecionado → caixa vazia

    def _load_layers(self, layers):
        self.ui.tableWidget.setRowCount(0)
        self.ui.tableWidget_2.setRowCount(0)
        for r, lyr in enumerate(layers):
            self.ui.tableWidget.insertRow(r)
            self.ui.tableWidget_2.insertRow(r)
            self.ui.tableWidget.setItem(r, 0, QTableWidgetItem(lyr.get("depth", "")))
            self.ui.tableWidget.setItem(r, 1, QTableWidgetItem(lyr.get("texture", "")))
        self.checkButton()

    def checkButton(self):
        has_rows = self.ui.tableWidget.rowCount() > 1
        self.ui.pushButton_4.setEnabled(has_rows)

    def deleteLayer(self) -> None:
        """Remove a camada selecionada (ou a última, se nada estiver selecionado)
        sincronizando TODAS as grades (principal, more-inputs, calculate/edit)."""
        tw_main = self.ui.tableWidget
        tw_more = self.ui.tableWidget_2
        tw_calc = self.tableCalc

        sm = tw_main.selectionModel()
        rows = sorted({idx.row() for idx in sm.selectedRows()}, reverse=True) if sm else []

        # se nada selecionado → remove a última linha, se existir
        if not rows and tw_main.rowCount() > 0:
            rows = [tw_main.rowCount() - 1]

        for row in rows:
            for tw in (tw_main, tw_more, tw_calc):
                tw.removeRow(row)

        self.checkButton()        # re-avalia o estado do botão “Delete”

    def goToFinalPage(self):
        self.ui.stackedWidget.setCurrentIndex(3)
    
    def goToPage2(self):
        self.ui.stackedWidget.setCurrentIndex(1)

    def goForward(self):
        current_index = self.ui.stackedWidget.currentIndex()
        next_index = current_index + 1
        self.ui.stackedWidget.setCurrentIndex(next_index)

    def goBack(self):
        current_index = self.ui.stackedWidget.currentIndex()
        self.ui.stackedWidget.setCurrentIndex(current_index - 1)

    def saveToDisk(self) -> None:
        """Write the pending profile to disk (File ▸ Save)."""
        if not self._pendingSave:
            QMessageBox.information(self, "Nothing to save",
                                     "There are no pending changes.")
            return

        data = self._pendingSave
        sol_path     = data["sol_path"]           # may be None
        current_code = data["current_code"]       # "" for a brand-new profile
        kwargs       = data["kwargs"]

        # ── if it’s a new profile, ask now for the 10-char code ─────
        if not kwargs["profile_id"]:
            pid, ok = QtWidgets.QInputDialog.getText(
                self, "Profile ID",
                "Enter the new profile code (10 characters):")
            if not ok:
                return
            pid = pid.strip().upper()
            if len(pid) != 10:
                QMessageBox.warning(self, "Error",
                                    "The code must be exactly 10 characters long.")
                return
            kwargs["profile_id"] = pid
            current_code = ""      # treat as brand-new (append)

        # ── do the actual I/O (leverages _write_profile) ────────────
        try:
            self._write_profile(kwargs["profile_id"], sol_path)
        except Exception as e:
            QMessageBox.critical(self, "Error",
                                 f"Could not save the profile:\n{e}")
            return

        # ── success: clear buffer & notify ──────────────────────────
        self._pendingSave = None
        QMessageBox.information(self, "Saved",
                                 "Profile saved successfully.")

    def handlePage0Ok(self):
        country          = self.ui.country_line.text()
        institute_code   = self.ui.instituteCode_line.text()
        site_name        = self.ui.siteName_line.text()
        latitude_txt     = self.ui.latitude_line.text().strip()
        longitude_txt    = self.ui.longitude_line.text().strip()
        soil_data_source = self.ui.soilData_line.text()
        soil_series      = self.ui.soilSeries_line.text()
        soil_classification = self.ui.soilClassification_line.text()

        # ── 1) Institute Code precisa de ≥2 caracteres ------------------------
        if len(institute_code.strip()) != 2:
            QMessageBox.warning(self, "Invalid institute code",
                                "Institute Code must contain exactly 2 characters.")
            return                                # permanece na página 0

        # ── 2) Latitude / Longitude ------------------------------------------ 
        #     • vazios → assume -99 (missing)
        #     • se não vazios → devem ser numéricos e dentro dos limites
        # ---------------------------------------------------------------------
        # latitude -------------------------------------------------------------
        if latitude_txt == "":
            lat = -99
            self.ui.latitude_line.setText("-99")     # opcional: escreve na caixa
        else:
            try:
                lat = float(latitude_txt)
            except ValueError:
                QMessageBox.warning(self, "Invalid latitude",
                                    "Latitude must be a number between -90 and 90 "
                                    "or left blank (defaults to -99).")
                return
            if lat != -99 and not (-90 <= lat <= 90):
                QMessageBox.warning(self, "Invalid latitude",
                                    "Latitude must be between -90 and 90 degrees.")
                return

        # longitude ------------------------------------------------------------
        if longitude_txt == "":
            lon = -99
            self.ui.longitude_line.setText("-99")     # opcional
        else:
            try:
                lon = float(longitude_txt)
            except ValueError:
                QMessageBox.warning(self, "Invalid longitude",
                                    "Longitude must be a number between -180 and 180 "
                                    "or left blank (defaults to -99).")
                return
            if lon != -99 and not (-180 <= lon <= 180):
                QMessageBox.warning(self, "Invalid longitude",
                                    "Longitude must be between -180 and 180 degrees.")
                return
        # ---------------------------------------------------------------------

        # ── tudo certo → avança para a próxima página -------------------------
        self.ui.stackedWidget.setCurrentIndex(1)

    def handlePage0Cancel(self):
        self.close()

    def handlePage1Ok(self):
        self.ui.stackedWidget.setCurrentIndex(2)

    def handlePage1Cancel(self):
        self.ui.stackedWidget.setCurrentIndex(0)

    def handlePage2Ok(self):
        self.ui.stackedWidget.setCurrentIndex(3)

    def handlePage2Cancel(self):
        self.ui.stackedWidget.setCurrentIndex(1)

    def handlePage3Ok(self):
        """
        Final OK on the wizard.

        • Collect the data the user entered.
        • Store it in memory (self._pendingSave).
        • Do NOT touch the disk and do NOT ask for a profile code here.
        """
        # ensure there is at least one layer
        layers = self._collect_layers()
        if not layers:
            QMessageBox.warning(self, "Error",
                                 "Add at least one soil layer before continuing.")
            return

        # profile code comes from the current profile (if any);
        # for a new profile we leave it blank and let File ▸ Save ask later
        pid = self.currentProfile["code"] if self.currentProfile else ""

        # collect header information (same fields used in _write_profile)
        kwargs = dict(
            profile_id          = pid,
            site                = self.ui.siteName_line.text() or "-99",
            country             = self.ui.country_line.text() or "-99",
            lat                 = float(self.ui.latitude_line.text() or 0),
            lon                 = float(self.ui.longitude_line.text() or 0),
            layers              = layers,
            salb                = float(self.ui.lineEdit_2.text() or 0.13),
            sldr                = float(self.ui.lineEdit_3.text() or 0.6),
            slro                = float(self.ui.lineEdit.text()  or 61),
            soil_data_source    = self.ui.soilData_line.text() or "-99",
            soil_series_name    = self.ui.soilSeries_line.text() or "-99",
            scs_family          = self.ui.soilClassification_line.text() or "-99",
            scom                = {
                "Black": "BL", "Brown": "BN", "Grey": "G",
                "Red": "R", "Yellow": "Y"
            }.get((self.ui.color_box.currentText() or "").strip(), ""),
        )

        # stage everything for a future File ▸ Save
        self._pendingSave = dict(
            sol_path     = Path(self.currentSolFile)
                           if self.currentSolFile else None,
            current_code = pid,          # may be empty for a new profile
            kwargs       = kwargs,
        )

        QMessageBox.information(
            self, "Ready",
            "Changes are now staged in memory.\n"
            "Choose File ▸ Save when you’re ready to write them to disk."
        )
        self.ui.stackedWidget.setCurrentIndex(0)   # back to the first page

    def handlePage3Cancel(self):
        self.ui.stackedWidget.setCurrentIndex(2)
    
    def openSoilFile(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Abrir Arquivo .SOL", "", "Arquivos DSSAT (*.SOL);;Todos os arquivos (*)", options=options)
    
        if file_name:
            try:
                with open(file_name, "r", encoding="utf-8") as f:
                    content = f.read()
                    QMessageBox.information(self, "Arquivo Aberto", f"Conteúdo do arquivo:\n\n{content[:500]}...\n\n(Truncado)")
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Não foi possível abrir o arquivo:\n{str(e)}")

from PyQt5.QtWidgets import QDialog
from profileList import Ui_Dialog

if __name__ == "__main__":
    import sys
    from logic import MainWindow
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())