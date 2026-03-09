import sys
import tempfile
from PyQt5.QtGui import QColor, QPixmap, QFont
import os
from typing import Optional
from pathlib import Path
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import (
    QFileDialog,
    QMessageBox,
    QComboBox,
    QDialog,
    QTableWidgetItem,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QWidget
)
from PyQt5.QtCore import Qt
import math
from sbuild import Ui_MainWindow
from profileList import Ui_Dialog, ProfileListDialog
from readSoilFile import read_profile, show_profiles
from createSoilFile import build_soil_file
from updateSoilFile import update_soil_file
from deleteSoilFile import delete_soil_profile
from hydrology import slope_from_cn, cn_to_group
from soil_utils import drainage_class

class MainWindow(QtWidgets.QMainWindow):
    
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.currentSolFile = None
        self._pendingSave = None
        self.currentProfile: Optional[dict] = None
        
        # Configura a página inicial (índice 0)
        self._setup_welcome_page()
        
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
        self.ui.actionOpen.triggered.connect(self.openSolFile)
        self.ui.actionClose_2.triggered.connect(self.closeSolFile)
        self.ui.actionEdit_3.triggered.disconnect()
        self.ui.actionSave_2.triggered.connect(self.writeSolFile)
        self.ui.actionEdit_3.triggered.connect(self.openProfileList)
        self.ui.actionDelete_3.triggered.connect(self.askDeleteProfile)
        self.ui.actionExit.triggered.connect(self.handlePage0Cancel)
        self.ui.actionNew_3.triggered.connect(self.newSolFile)
        self.ui.actionSave_as_2.triggered.connect(self.saveAsFile)
        self.ui.stackedWidget.currentChanged.connect(self._on_page_changed)
        self._prepare_combo(self.ui.color_box)
        self._prepare_combo(self.ui.drainage_box)
        self._prepare_combo(self.ui.runoffPotential_box)

        # limites de caracteres General Information 
        for field in (self.ui.country_line,
                      self.ui.siteName_line,
                      self.ui.soilData_line):
            field.setMaxLength(11)
        for field in (self.ui.soilSeries_line,
                      self.ui.soilClassification_line):
            field.setMaxLength(50)
        
        self.fileStatusAction = QtWidgets.QAction("", self)
        self.fileStatusAction.setEnabled(False)
        mb = self.menuBar()
        assert mb is not None, "menuBar não inicializado"
        mb.addAction(self.fileStatusAction)
        mb.setStyleSheet("QMenuBar::item:disabled { color: black; }")

    def _setup_welcome_page(self):
        """Configura a página inicial (newFile_page0) com logo e texto SBuild"""
        page0 = self.ui.newFile_page0
        
        # Remove qualquer layout existente
        if page0.layout():
            QWidget().setLayout(page0.layout())
        
        # Layout principal centralizado
        main_layout = QVBoxLayout(page0)
        main_layout.setAlignment(Qt.AlignCenter)
        
        # Container para logo e texto
        container = QWidget()
        h_layout = QHBoxLayout(container)
        h_layout.setAlignment(Qt.AlignCenter)
        h_layout.setSpacing(20)
        
        # Logo
        logo_label = QLabel()
        logo_path = os.path.join(os.path.dirname(__file__), 'ui_files', 'Logo.png')
        
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            scaled_pixmap = pixmap.scaled(
                350, 250, 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            logo_label.setPixmap(scaled_pixmap)
        else:
            # Fallback se a logo não for encontrada
            logo_label.setText("[Logo not found]")
            logo_label.setStyleSheet("font-size: 20px; color: red;")
            print(f"Logo não encontrada em: {logo_path}")
        
        h_layout.addWidget(logo_label)
        
        # Texto "SBuild"
        text_label = QLabel("SBuild")
        font = QFont("Arial", 80, QFont.Bold)
        text_label.setFont(font)
        text_label.setStyleSheet("color: black;")
        h_layout.addWidget(text_label)
        
        main_layout.addWidget(container)
        
        # Mensagem de instrução
        hint_label = QLabel("Open or create a new soil file")
        hint_font = QFont("Arial", 14)
        hint_label.setFont(hint_font)
        hint_label.setStyleSheet("color: #555555;")
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter) 
        main_layout.addWidget(hint_label)

    def addLayer(self) -> None:
        """Adiciona uma nova camada (+ 5 cm) sincronizando as grades."""
        tw1 = self.ui.tableWidget          # grade principal
        tw2 = self.ui.tableWidget_2        # "More inputs"
        tw3 = self.tableCalc               # "Calculate/Edit Soil Parameters"
        r   = tw1.rowCount()               # índice da nova linha

        # profundidade 
        if r == 0:
            depth_val = 5
        else:
            try:
                depth_val = int(tw1.item(r - 1, 0).text()) + 5
            except Exception:
                depth_val = 5

        _ro = Qt.ItemIsEnabled | Qt.ItemIsSelectable  # type: ignore[attr-defined]

        # insere linha nas três tabelas
        for tw in (tw1, tw2, tw3):
            tw.insertRow(r)
            depth_item = QTableWidgetItem(str(depth_val))
            if tw in (tw2, tw3):   # More Inputs e Calculate/Edit: depth read-only
                depth_item.setFlags(_ro)
            tw.setItem(r, 0, depth_item)

        # coluna "Master horizon" (grade principal) com default –99
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

        # zera variáveis de estado 
        self.currentSolFile = None
        self.currentProfile = None
        self.fileStatusAction.setText("")

        # limpa campos "General Information"
        self.cleanFields()

        # limpa superfície (aba Page 1)
        self.ui.color_box.setCurrentIndex(-1)
        self.ui.drainage_box.setCurrentIndex(-1)
        self.ui.runoffPotential_box.setCurrentIndex(-1)
        self.ui.slope_line.clear()
        self.ui.fertilityFactor_line.clear()

        # limpa campos da aba "Calculate/Edit soil parameters" 
        self.ui.lineEdit.clear()      # Runoff Curve Number
        self.ui.lineEdit_2.clear()    # Albedo
        self.ui.lineEdit_3.clear()    # Drainage Rate

        # limpa as três tabelas de camadas 
        for tw in (self.ui.tableWidget,
                   self.ui.tableWidget_2,
                   self.tableCalc):
            tw.setRowCount(0)

        self.checkButton()            # atualiza estado do botão Delete
        self.ui.stackedWidget.setCurrentIndex(0)

    def newSolFile(self) -> None:
        # limpa estado e campos
        self.currentSolFile = None
        self.currentProfile = None
        self.fileStatusAction.setText("")
        self.cleanFields()
        self.ui.color_box.setCurrentIndex(-1)
        self.ui.drainage_box.setCurrentIndex(-1)
        self.ui.runoffPotential_box.setCurrentIndex(-1)
        self.ui.slope_line.clear()
        self.ui.fertilityFactor_line.clear()
        self.ui.lineEdit.clear()
        self.ui.lineEdit_2.clear()
        self.ui.lineEdit_3.clear()
        for tw in (self.ui.tableWidget, self.ui.tableWidget_2, self.tableCalc):
            tw.setRowCount(0)
        self.checkButton()

        # avança para General Information
        self.ui.stackedWidget.setCurrentIndex(1)

    def saveAsFile(self) -> None:
        """Escolhe destino e grava o estado atual como um novo arquivo .SOL."""
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Save As",
            "",
            "DSSAT Soil Files (*.SOL);;All files (*)",
        )
        if not file_name:
            return
        if not file_name.upper().endswith(".SOL"):
            file_name += ".SOL"
        # cria arquivo vazio com cabeçalho e define como atual
        Path(file_name).write_text("*SOILS: General DSSAT Soil Input File\n\n",
                                   encoding="utf-8")
        self.setCurrentSolFile(file_name)
        self.currentProfile = None
        # grava o conteúdo atual
        self.writeSolFile()

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
        # caminho e código do .SOL 
        sol0 = self.getCurrentSolFile()
        if sol0 is None:
            QMessageBox.warning(self, "Warning", "No .SOL file opened.")
            return
        sol: str = sol0
        code = profile["code"]
        data = read_profile(sol, code)

        # General Information 
        self.ui.country_line.setText(data["country"])
        self.ui.siteName_line.setText(data["site_name"])
        self.ui.instituteCode_line.setText(data["institute_code"])
        self.ui.latitude_line.setText(data["latitude"])
        self.ui.longitude_line.setText(data["longitude"])
        self.ui.soilData_line.setText(data["soil_data_source"])
        self.ui.soilSeries_line.setText(data["soil_series_name"])
        self.ui.soilClassification_line.setText(data["soil_classification"])

        # Surface Information 
        cmap = {
            "BL": "Black", "BK": "Black",
            "BN": "Brown", "BR": "Brown",
            "G":  "Grey",  "GY": "Grey",
            "R":  "Red",   "RD": "Red",
            "Y":  "Yellow","YL": "Yellow",
        }

        # Color 
        cmap = {
            "BL": "Black", "BK": "Black", "BLA": "Black", "BLAC": "Black", "BLACK": "Black",
            "BN": "Brown", "BR": "Brown", "BRO": "Brown", "BROW": "Brown", "BROWN": "Brown",
            "G":  "Grey",  "GY": "Grey",  "GR":  "Grey",  "GREY": "Grey",  "GRAY": "Grey",
            "R":  "Red",   "RD": "Red",   "RED": "Red",
            "Y":  "Yellow","YL": "Yellow","YEL": "Yellow","YELL": "Yellow","YELLOW": "Yellow",
        }
        code_color = (data.get("color_code") or "").strip().upper()
        color_name = cmap.get(code_color, "")

        # fallback: deduz cor do albedo SALB quando SCOM está ausente
        if not color_name:
            try:
                salb = float(data.get("albedo") or -1)
                if 0.07 <= salb <= 0.11:
                    color_name = "Black"
                elif 0.11 < salb <= 0.135:
                    color_name = "Brown"
                elif 0.135 < salb <= 0.155:
                    color_name = "Red"
                elif 0.155 < salb <= 0.175:
                    color_name = "Yellow"
            except (TypeError, ValueError):
                pass

        if color_name:
            self.ui.color_box.setCurrentText(color_name)
        else:
            self.ui.color_box.setCurrentIndex(-1)

        # Drainage class
        try:
            dr_val = float(data["drainage_rate"])
        except (TypeError, ValueError):
            dr_val = None

        label = drainage_class(dr_val)
        
        if label:
            self.ui.drainage_box.setCurrentText(label)
        else:
            self.ui.drainage_box.setCurrentIndex(-1)

        # Runoff potential e % slope
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
                self.ui.runoffPotential_box.setCurrentText(cn_to_group(rc))
            else:
                self.ui.runoffPotential_box.setCurrentIndex(-1)
        
        else:
            if rc > 0:
                txt_ro = cn_to_group(rc)
                self.ui.runoffPotential_box.setCurrentText(txt_ro)
                slope_val = slope_from_cn(txt_ro, int(rc))
                self.ui.slope_line.setText("" if slope_val is None else str(slope_val))
            else:
                self.ui.runoffPotential_box.setCurrentIndex(-1)
                self.ui.slope_line.clear()

        ff = data.get("fertility_factor")
        self.ui.fertilityFactor_line.setText("" if ff in (None, "", "-99") else str(ff))

        # Surface parameters widgets na aba Calculate/Edit soil parameters
        rc_val = data.get("runoff_curve")
        self.ui.lineEdit.setText("" if rc_val in (None, "", "-99") else str(rc_val))  # SLRO
        salb_val = data.get("albedo")
        self.ui.lineEdit_2.setText("" if salb_val in (None, "", "-99") else str(salb_val))  # SALB
        sldr_val = data.get("drainage_rate")
        self.ui.lineEdit_3.setText("" if sldr_val in (None, "", "-99") else str(sldr_val))  # SLDR

        # Layers tables (principal, more inputs e calculate)
        tw_main = self.ui.tableWidget
        tw_more = self.ui.tableWidget_2
        tw_calc = self.tableCalc          # grade da aba Calculate/Edit soil parameters

        # limpa todas
        for tw in (tw_main, tw_more, tw_calc):
            tw.setRowCount(0)

        # ordem exata das colunas de cada grade
        main_keys = ["depth", "texture", "clay", "silt",
                    "stones", "oc", "ph", "cec", "tn"]

        # grade de cálculo
        calc_keys = ["depth", "clay", "silt", "stones",
                    "lll", "dul", "sat", "bd", "ksat", "srgf"]

        for layer in data.get("layers", []):
            r = tw_main.rowCount()

            # cria linha nas três grades
            for tw in (tw_main, tw_more, tw_calc):
                tw.insertRow(r)

            # grade principal 
            for c, k in enumerate(main_keys):
                tw_main.setItem(r, c, QTableWidgetItem(layer.get(k, "")))

            # grade de more inputs
            _ro2 = Qt.ItemIsEnabled | Qt.ItemIsSelectable  # type: ignore[attr-defined]
            depth_item = QTableWidgetItem(layer.get("depth", ""))
            depth_item.setFlags(_ro2)
            tw_more.setItem(r, 0, depth_item)

            # grade de cálculo
            _ro = Qt.ItemIsEnabled | Qt.ItemIsSelectable  # type: ignore[attr-defined]
            for c, k in enumerate(calc_keys):
                item = QTableWidgetItem(layer.get(k, ""))
                if c < 4:          # depth, clay, silt, stones read only
                    item.setFlags(_ro)
                tw_calc.setItem(r, c, item)

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
        if not file_name:
            return  # Usuário cancelou

        self.setCurrentSolFile(file_name)
        self.currentProfile = None
        self.ui.stackedWidget.setCurrentIndex(1)
    
    def setCurrentSolFile(self, file_name: str):
        self.currentSolFile = file_name
        full_path = os.path.abspath(file_name)
        self.fileStatusAction.setText(f"Working with file {full_path}")

    def closeProfile(self) -> None:
        """
        Resets the UI back to the "no-profile-selected" state without
        closing the .SOL file itself.
        """
        if self.currentProfile is None:
            return

        # forget the selection
        self.currentProfile = None

        # clear General Information fields
        self.cleanFields()

        # reset surface widgets (Page 1)
        self.ui.color_box.setCurrentIndex(-1)
        self.ui.drainage_box.setCurrentIndex(-1)
        self.ui.runoffPotential_box.setCurrentIndex(-1)
        self.ui.slope_line.clear()
        self.ui.fertilityFactor_line.clear()

        # reset Calculate/Edit soil parameters widgets (Page 2)
        self.ui.lineEdit.clear()      # SLRO
        self.ui.lineEdit_2.clear()    # SALB
        self.ui.lineEdit_3.clear()    # SLDR

        # wipe the three layer tables
        for tw in (self.ui.tableWidget,
                self.ui.tableWidget_2,
                self.tableCalc):
            tw.setRowCount(0)

        # update buttons that depend on row count
        self.checkButton()

        self.ui.stackedWidget.setCurrentIndex(1)

    def getCurrentSolFile(self) -> Optional[str]:
        return self.currentSolFile
    
    def _collect_layers(self) -> list[dict]:
        """Lê todas as linhas da grade principal e devolve [{SLB, SLLL, …}, …]."""
        tw_main = self.ui.tableWidget
        tw_more = self.ui.tableWidget_2
        tw_calc = self.tableCalc

        layers: list[dict] = []
        for r in range(tw_main.rowCount()):
            try:  # profundidade é obrigatória
                slb = int(float(tw_main.item(r, 0).text()) + 0.5)
            except Exception:
                continue     # pula linhas vazias

            layer = {
                # grade principal
                "slb":  slb,
                "slmh":   tw_main.item(r, 1).text()  if tw_main.item(r, 1)  else "-99",
                "slcl":   tw_main.item(r, 2).text()  if tw_main.item(r, 2)  else -99,
                "slsi":   tw_main.item(r, 3).text()  if tw_main.item(r, 3)  else -99,
                "slcf":   tw_main.item(r, 4).text()  if tw_main.item(r, 4)  else -99,
                "sloc":   tw_main.item(r, 5).text()  if tw_main.item(r, 5)  else -99,
                "slhw":   tw_main.item(r, 6).text()  if tw_main.item(r, 6)  else -99,
                "scec":   tw_main.item(r, 7).text()  if tw_main.item(r, 7)  else -99,
                "slni":   tw_main.item(r, 8).text()  if tw_main.item(r, 8)  else -99,
                # more inputs
                "slpa":   tw_more.item(r, 1).text()  if tw_more.item(r, 1)  else "-99",
                "slpb":   tw_more.item(r, 2).text()  if tw_more.item(r, 2)  else "-99",
                "caco3":  tw_more.item(r, 3).text()  if tw_more.item(r, 3)  else "-99",
                "slal":   tw_more.item(r, 4).text()  if tw_more.item(r, 4)  else "-99",
                "slke":   tw_more.item(r, 5).text()  if tw_more.item(r, 5)  else "-99",
                "sadc":   tw_more.item(r, 6).text()  if tw_more.item(r, 6)  else "-99",
                "slca":   tw_more.item(r, 7).text()  if tw_more.item(r, 7)  else "-99",
                # grade de cálculo
                "slll":   tw_calc.item(r, 4).text()  if tw_calc.item(r, 4)  else -99,
                "sdul":   tw_calc.item(r, 5).text()  if tw_calc.item(r, 5)  else -99,
                "ssat":   tw_calc.item(r, 6).text()  if tw_calc.item(r, 6)  else -99,
                "sbdm":   tw_calc.item(r, 7).text()  if tw_calc.item(r, 7)  else -99,
                "ssks":   tw_calc.item(r, 8).text()  if tw_calc.item(r, 8)  else -99,
                "srgf":   tw_calc.item(r, 9).text()  if tw_calc.item(r, 9)  else -99,
            }
            layers.append(layer)
        return layers

    def _sync_calc_from_main(self) -> None:
        """
        Copia Depth, Clay, Silt e Stones da grade principal 
        para a grade Calculate/Edit soil parameters
        Só é chamada quando se é criado um novo perfil.
        """
        tw_main = self.ui.tableWidget      # grade Input table
        tw_calc = self.tableCalc           # grade Calculate/Edit soil parameters

        rows = tw_main.rowCount()
        tw_calc.setRowCount(rows)          # garante mesmo número de linhas

        _READ_ONLY = Qt.ItemIsEnabled | Qt.ItemIsSelectable  # type: ignore[attr-defined]

        for r in range(rows):
            mapping = {
                0: 0,   # Depth > Depth
                2: 1,   # Clay > Clay
                3: 2,   # Silt > Silt
                4: 3,   # Stones > Stones
            }
            for src_col, dst_col in mapping.items():
                src_item = tw_main.item(r, src_col)
                text = src_item.text() if src_item else ""
                item = QTableWidgetItem(text)
                item.setFlags(_READ_ONLY)
                tw_calc.setItem(r, dst_col, item)

    _CALC_PAGE_INDEX       = 4   # goToFinalPage > setCurrentIndex(4)
    _MORE_INPUTS_PAGE_INDEX = 3  # More Inputs > setCurrentIndex(3)

    def _on_page_changed(self, idx: int) -> None:
        if self.currentProfile is not None:
            return
        _ro = Qt.ItemIsEnabled | Qt.ItemIsSelectable  # type: ignore[attr-defined]
        tw_main = self.ui.tableWidget
        if idx == self._MORE_INPUTS_PAGE_INDEX:
            # sincroniza depth do Input Table para More Inputs
            tw_more = self.ui.tableWidget_2
            for r in range(tw_main.rowCount()):
                src = tw_main.item(r, 0)
                item = QTableWidgetItem(src.text() if src else "")
                item.setFlags(_ro)
                tw_more.setItem(r, 0, item)
        elif idx == self._CALC_PAGE_INDEX:
            self._sync_calc_from_main()

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

        # header
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

        if sol_path is None:    # 1) novo arquivo
            dest = QFileDialog.getSaveFileName(self,
                                            "Salvar novo arquivo .SOL",
                                            f"{profile_id}.SOL",
                                            "Arquivos DSSAT (*.SOL)")[0]
            if not dest:    # cancelado
                return
            build_soil_file(dest=dest, **kwargs)

        elif self.currentProfile is None:   # 2) append a novo perfil
            # cria arquivo temporário provisório
            with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".SOL", mode="w", encoding="utf-8") as tf:
                tmp_path = Path(tf.name)

            build_soil_file(dest=tmp_path, **kwargs)    # gera bloco sozinho

            # carrega o bloco recém criado
            new_block = "\n".join(
                tmp_path.read_text(encoding="utf-8").splitlines()[2:]
            )
            tmp_path.unlink()   # remove o temporário

            # anexa ao .SOL original
            with open(sol_path, "r+", encoding="utf-8") as f:
                content = f.read()

                # prefixo que gera sempre uma linha vazia de separação
                if content.endswith("\n"):
                    prefix = "\n"          # já havia \n final: adiciona mais 1
                else:
                    prefix = "\n\n"        # faltava \n final: fecha e cria a vazia

                if not new_block.endswith("\n"):
                    new_block += "\n"

                # grava depois do EOF
                f.seek(0, os.SEEK_END)
                f.write(prefix + new_block)
        
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
        # Calculate missing values: LL, DUL, SAT, BD, Ksat, SRGF.
        # If OC present for ALL layers: Rawls et al. (1982) for LL/DUL/SAT.
        # If OC missing for ANY layer:  Saxton et al. (1986) for LL/DUL/SAT.
        # BD: Rawls & Brakensiek (1985).
        # Ksat: Saxton et al. (1986).
        # SRGF: exp(-0.02 * center) if center > 20 cm, else 1.0.
        tw      = self.tableCalc
        tw_main = self.ui.tableWidget
        n       = tw.rowCount()

        BLUE = QColor(200, 225, 255)

        def num_c(r: int, c: int) -> float | None:
            # Read float from Calculate/edit soil parameters table, none if empty or -99.
            item = tw.item(r, c)
            if not item: return None
            try:
                v = float(item.text())
                return None if v == -99 else v
            except Exception:
                return None

        def num_m(r: int, c: int) -> float | None:
            # Read float from main table, none if empty or -99.
            item = tw_main.item(r, c)
            if not item: return None
            try:
                v = float(item.text())
                return None if v == -99 else v
            except Exception:
                return None

        def put(r: int, c: int, value: float, fmt: str = ".3f") -> None:
            # Write to cell only if it was empty then highlight in blue.
            if tw.item(r, c):
                return
            it = QTableWidgetItem(format(value, fmt))
            it.setBackground(BLUE)
            tw.setItem(r, c, it)

        # Pre-check: clay and silt must be present in every layer
        for r in range(n):
            if num_c(r, 1) is None or num_c(r, 2) is None:
                QMessageBox.warning(self, "Missing texture",
                                    "Each layer needs % clay and % silt "
                                    "before running this calculation.")
                return

        # Method selection based on OC availability
        use_rawls = all(num_m(r, 5) is not None for r in range(n))

        prev_depth = 0.0
        for r in range(n):
            clay  = num_c(r, 1)   # % clay
            silt  = num_c(r, 2)   # % silt
            assert clay is not None and silt is not None
            sand  = max(0.0, 100.0 - clay - silt)
            depth = num_c(r, 0) 

            # Center of layer used for SRGF
            bottom = depth if depth is not None else prev_depth + 10.0
            center = (prev_depth + bottom) / 2.0
            prev_depth = bottom

            # OC from main table 
            # OM = OC × 1.724
            oc = num_m(r, 5)
            om = oc * 1.724 if oc is not None else 0.0

            # Porosity and θ_SAT (Rawls & Brakensiek 1985)
            # porosity for BD: φ = 0.299 - 7.251e-4·S + 0.1276·log10(C) + 0.019·OM
            # θ_SAT: 0.273 - 7.251e-4·S + 0.1276·log10(C) + 0.015·OM
            log10c = math.log10(clay) if clay > 0 else 0.0
            porosity = max(0.0, 0.299 - 0.0007251*sand + 0.1276*log10c + 0.019*om)
            theta_sat = max(0.0, 0.273 - 0.0007251*sand + 0.1276*log10c + 0.015*om)

            # Bulk density: ρb = (1-φ)·2.65
            bd = num_c(r, 7)
            if bd is None:
                bd = max(0.1, min(2.65, (1.0 - porosity) * 2.65))
                put(r, 7, bd, ".2f")

            # LL, DUL, SAT
            if use_rawls:
                # Rawls et al. (1982) Table 3, Row 1: S, C in %, OM in %
                theta_dul = 0.2576 - 0.0020*sand + 0.0036*clay + 0.0299*om
                theta_ll  = 0.0260 + 0.0050*clay + 0.0158*om

                put(r, 4, max(0.0, theta_ll))
                put(r, 5, max(0.0, theta_dul))
                put(r, 6, max(0.0, theta_sat))

            else:
                # Saxton et al. (1986) Eq. 5-6: S, C in %
                # ψ (kPa) = A × θ^B  →  θ = (ψ/A)^(1/B)
                # A × 100 converts bars → kPa
                C = clay
                S = sand
                A = math.exp(-4.396 - 0.0715*C
                             - 0.000488*S**2 - 0.00004285*S**2*C) * 100.0
                B = -3.140 - 0.00222*C**2 - 0.00003484*S**2*C

                if A > 0 and B < 0:
                    theta_ll  = (1500.0 / A) ** (1.0 / B)   # 1500 kPa = WP
                    theta_dul = (33.0   / A) ** (1.0 / B)   # 33 kPa = FC

                    put(r, 4, max(0.0, theta_ll))
                    put(r, 5, max(0.0, theta_dul))
                    put(r, 6, max(0.0, theta_sat))

            # Ksat (Saxton 1986 Eq. 10)
            # KS (cm/h) = exp[(12.012 - 0.0755·S) + (-3.895 + 0.03671·S
            #              - 0.1103·C + 0.00087546·C²) / θ_SAT]
            # 2.778e-6 m/s = 1.0 cm/h, so result is directly in cm/h
            if num_c(r, 8) is None and theta_sat > 0:
                try:
                    ln_k = ((12.012 - 0.0755*sand)
                            + (-3.895 + 0.03671*sand
                               - 0.1103*clay + 0.00087546*clay**2) / porosity)
                    ksat = math.exp(ln_k)   # cm/h
                    put(r, 8, max(0.0, ksat), ".3f")
                except Exception:
                    pass

            # SRGF
            # If center > 20: SRGF = exp(-0.02 × center); else SRGF = 1.0
            if num_c(r, 9) is None:
                srgf = 1.0 if center <= 20.0 else math.exp(-0.02 * center)
                put(r, 9, max(0.0, srgf), ".3f")

        QMessageBox.information(self, "Done",
                                "Missing hydraulic values calculated.")

    def writeSolFile(self) -> None:
        # arquivo aberto?
        sol = self.getCurrentSolFile()
        if not sol or not Path(sol).exists():
            QMessageBox.warning(self, "Warning",
                                "No .SOL file opened for editing.")
            return

        # pelo menos uma camada
        layers = self._collect_layers()
        if not layers:
            QMessageBox.warning(self, "Error",
                                "Add at least one soil layer before saving.")
            return

        # A) Perfil selecionado: atualizar bloco existente

        if self.currentProfile:
            def _f_or_none(txt):
                t = (txt or "").strip()
                if t == "": return None
                try: return float(t)
                except Exception: return None

            code = self.currentProfile["code"]

            updates = {
                "site":      self.ui.siteName_line.text()  or "-99",
                "country":   self.ui.country_line.text()   or "-99",

                "lat":  float(self.ui.latitude_line.text()  or 0),
                "long": float(self.ui.longitude_line.text() or 0),
                "scom": {"Black":"BL","Brown":"BN","Grey":"G","Red":"R","Yellow":"Y"}.get((self.ui.color_box.currentText() or "").strip(), ""),

                "soil_series_name": self.ui.soilSeries_line.text(),
                "scs_family":       self.ui.soilClassification_line.text(),
                "salb": float(self.ui.lineEdit_2.text() or 0.13),
                "sldr": float(self.ui.lineEdit_3.text() or 0.60),
                "slro": float(self.ui.lineEdit.text()  or 61),

                # "soil_data_source": self.ui.soilData_line.text() or "-99",

                "layers": layers,   # mantém as camadas
            }

            try:
                update_soil_file(sol, code, updates)
                QMessageBox.information(self, "OK",
                    f"Soil profile «{code}» updated successfully in «{sol}».")
            except Exception as e:
                QMessageBox.critical(self, "Error",
                                    f"Failed to save:\n{e}")
            return

        # B) Nenhum perfil selecionado: criar novo bloco e anexar

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
            # _write_profile() extrai todos os campos da UI e, como self.currentProfile é None, faz o append correto.
            self._write_profile(pid, Path(sol))
            QMessageBox.information(self, "OK",
                f"New soil profile «{pid}» added to «{sol}».")
        except Exception as e:
            QMessageBox.critical(self, "Error",
                                f"Failed to save:\n{e}")

    def askDeleteProfile(self):                                  
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

    def _prepare_combo(self, combo: QComboBox):
        combo.setEditable(False)       
        combo.setInsertPolicy(QComboBox.NoInsert)   
        combo.setCurrentIndex(-1)

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
        """Remove a camada selecionada ou a última, se nada estiver selecionado
        sincronizando todas as grades."""
        tw_main = self.ui.tableWidget
        tw_more = self.ui.tableWidget_2
        tw_calc = self.tableCalc

        sm = tw_main.selectionModel()
        rows = sorted({idx.row() for idx in sm.selectedRows()}, reverse=True) if sm else []

        # se nada selecionado, remove a última linha
        if not rows and tw_main.rowCount() > 0:
            rows = [tw_main.rowCount() - 1]

        for row in rows:
            for tw in (tw_main, tw_more, tw_calc):
                tw.removeRow(row)

        self.checkButton()  # reavalia o estado do botãto Delete

    def goToFinalPage(self):
        self.ui.stackedWidget.setCurrentIndex(4)

    def goToPage2(self):
        self.ui.stackedWidget.setCurrentIndex(2)

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

        # if it’s a new profile, ask now for the 10 character code
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
            current_code = ""

        try:
            self._write_profile(kwargs["profile_id"], sol_path)
        except Exception as e:
            QMessageBox.critical(self, "Error",
                                 f"Could not save the profile:\n{e}")
            return

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

        # Institute Code precisa de 2 caracteres
        if len(institute_code.strip()) != 2:
            QMessageBox.warning(self, "Invalid institute code",
                                "Institute Code must contain exactly 2 characters.")
            return                               

        # latitude 
        if latitude_txt == "":
            lat = -99
            self.ui.latitude_line.setText("-99")
        else:
            try:
                lat = float(latitude_txt)
            except ValueError:
                QMessageBox.warning(self, "Invalid latitude",
                                    "Latitude must be a number between -90 and 90 ")
                return
            if lat != -99 and not (-90 <= lat <= 90):
                QMessageBox.warning(self, "Invalid latitude",
                                    "Latitude must be between -90 and 90 degrees.")
                return

        # longitude 
        if longitude_txt == "":
            lon = -99
            self.ui.longitude_line.setText("-99")
        else:
            try:
                lon = float(longitude_txt)
            except ValueError:
                QMessageBox.warning(self, "Invalid longitude",
                                    "Longitude must be a number between -180 and 180 ")
                return
            if lon != -99 and not (-180 <= lon <= 180):
                QMessageBox.warning(self, "Invalid longitude",
                                    "Longitude must be between -180 and 180 degrees.")
                return
            
        # % Slope
        slope_txt = self.ui.slope_line.text().strip()
        if slope_txt:
            try:
                slope_val = float(slope_txt)
                if not (0 <= slope_val <= 100):
                    QMessageBox.warning(self, "Invalid % Slope",
                                        "% Slope must be between 0 and 100.")
                    return
            except ValueError:
                QMessageBox.warning(self, "Invalid % Slope",
                                    "% Slope must be a number between 0 and 100.")
                return

        # Fertility Factor
        ff_txt = self.ui.fertilityFactor_line.text().strip()
        if ff_txt:
            try:
                ff_val = float(ff_txt)
                if not (0.0 <= ff_val <= 1.0):
                    QMessageBox.warning(self, "Invalid Fertility Factor",
                                        "Fertility Factor must be between 0 and 1.")
                    return
            except ValueError:
                QMessageBox.warning(self, "Invalid Fertility Factor",
                                    "Fertility Factor must be a number between 0 and 1.")
                return

        # avança para a próxima página
        self.ui.stackedWidget.setCurrentIndex(2)

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
        def _dssat_decimal_ok(txt: str) -> bool:
            """
            DSSAT decimal digit rule: if the value contains a decimal point,
            the integer part (everything before '.', including sign) must be
            at most 3 characters long.  E.g. "-99.5" OK, "-999.5" NOT OK.
            """
            if '.' not in txt:
                return True
            int_part = txt.split('.')[0]
            return len(int_part) <= 3

        # Albedo (SALB) 0-99, accepts -99
        salb_txt = self.ui.lineEdit_2.text().strip()
        if salb_txt and salb_txt != "-99":
            try:
                salb_val = float(salb_txt)
                if not (0 <= salb_val <= 99):
                    QMessageBox.warning(self, "Invalid Albedo",
                                        "Albedo (SALB) must be between 0 and 99.")
                    return
            except ValueError:
                QMessageBox.warning(self, "Invalid Albedo",
                                    "Albedo must be a number.")
                return

        # Runoff Curve Number (SLRO) 0-999, accepts -99
        slro_txt = self.ui.lineEdit.text().strip()
        if slro_txt and slro_txt != "-99":
            try:
                slro_val = float(slro_txt)
                if not (0 <= slro_val <= 999):
                    QMessageBox.warning(self, "Invalid Runoff Curve Number",
                                        "Runoff Curve Number (SLRO) must be between 0 and 999.")
                    return
            except ValueError:
                QMessageBox.warning(self, "Invalid Runoff Curve Number",
                                    "Runoff Curve Number must be a number between 0 and 999.")
                return

        # Drainage Rate (SLDR) 0-999, accepts -99
        sldr_txt = self.ui.lineEdit_3.text().strip()
        if sldr_txt and sldr_txt != "-99":
            try:
                sldr_val = float(sldr_txt)
                if not (0 <= sldr_val <= 999):
                    QMessageBox.warning(self, "Invalid Drainage Rate",
                                        "Drainage Rate (SLDR) must be between 0 and 999.")
                    return
            except ValueError:
                QMessageBox.warning(self, "Invalid Drainage Rate",
                                    "Drainage Rate must be a number between 0 and 999.")
                return

        # At least one layer
        layers = self._collect_layers()
        if not layers:
            QMessageBox.warning(self, "Error",
                                 "Add at least one soil layer before continuing.")
            return

        # Layer depth: positive, <= 600, strictly increasing
        prev_depth = 0
        for i, layer in enumerate(layers):
            d = layer["slb"]
            if d <= 0:
                QMessageBox.warning(self, "Invalid layer depth",
                                    f"Layer {i+1}: depth must be a positive value.")
                return
            if d > 600:
                QMessageBox.warning(self, "Invalid layer depth",
                                    f"Layer {i+1}: depth ({d} cm) cannot exceed 600 cm.")
                return
            if d <= prev_depth:
                QMessageBox.warning(self, "Invalid layer depth",
                                    f"Layer {i+1}: depth ({d} cm) must be greater "
                                    f"than the previous layer ({prev_depth} cm).")
                return
            prev_depth = d

        for i, layer in enumerate(layers):
            lbl = f"Layer {i+1}"

            # Master Horizon: -999 to 99999 decimal digit rule
            slmh_txt = str(layer.get("slmh", "")).strip()
            if slmh_txt and slmh_txt not in ("-99", ""):
                try:
                    slmh_val = float(slmh_txt)
                    if not (-999 <= slmh_val <= 99999):
                        QMessageBox.warning(self, "Invalid Master Horizon",
                                            f"{lbl}: Master Horizon must be between -999 and 99999.")
                        return
                    if not _dssat_decimal_ok(slmh_txt):
                        QMessageBox.warning(self, "Invalid Master Horizon",
                                            f"{lbl}: Master Horizon integer part must be ≤ 3 digits.")
                        return
                except ValueError:
                    pass

            # Clay and Silt: 0-100, both missing or both present and sum has to be <= 100
            clay_txt = str(layer.get("slcl", "")).strip()
            silt_txt = str(layer.get("slsi", "")).strip()
            clay_missing = clay_txt in ("-99", "")
            silt_missing = silt_txt in ("-99", "")
            if clay_missing != silt_missing:
                QMessageBox.warning(self, "Invalid texture",
                                    f"{lbl}: Clay and Silt must both be provided or both be -99.")
                return
            try:
                clay = 0.0
                silt = 0.0
                if not clay_missing:
                    clay = float(clay_txt)
                    if not (0 <= clay <= 100):
                        QMessageBox.warning(self, "Invalid clay content",
                                            f"{lbl}: clay must be between 0 and 100%.")
                        return
                if not silt_missing:
                    silt = float(silt_txt)
                    if not (0 <= silt <= 100):
                        QMessageBox.warning(self, "Invalid silt content",
                                            f"{lbl}: silt must be between 0 and 100%.")
                        return
                if not clay_missing and not silt_missing:
                    if clay + silt > 100:
                        QMessageBox.warning(self, "Invalid texture",
                                            f"{lbl}: clay ({clay}%) + silt ({silt}%) cannot exceed 100%.")
                        return
            except ValueError:
                pass

            # Stones: 0-100, accepts -99
            slcf_txt = str(layer.get("slcf", "")).strip()
            if slcf_txt and slcf_txt not in ("-99", ""):
                try:
                    slcf_val = float(slcf_txt)
                    if not (0 <= slcf_val <= 100):
                        QMessageBox.warning(self, "Invalid Stones",
                                            f"{lbl}: Stones must be between 0 and 100%.")
                        return
                except ValueError:
                    pass

            # Organic Carbon: 0-58, accepts -99
            sloc_txt = str(layer.get("sloc", "")).strip()
            if sloc_txt and sloc_txt not in ("-99", ""):
                try:
                    sloc_val = float(sloc_txt)
                    if not (0 <= sloc_val <= 58):
                        QMessageBox.warning(self, "Invalid Organic Carbon",
                                            f"{lbl}: Organic Carbon must be between 0 and 58.")
                        return
                except ValueError:
                    pass

            # pH: 0-14, accepts -99
            slhw_txt = str(layer.get("slhw", "")).strip()
            if slhw_txt and slhw_txt not in ("-99", ""):
                try:
                    slhw_val = float(slhw_txt)
                    if not (0 <= slhw_val <= 14):
                        QMessageBox.warning(self, "Invalid pH",
                                            f"{lbl}: pH must be between 0 and 14.")
                        return
                except ValueError:
                    pass

            # CEC: 0-99999, accepts -99 and decimal digit rule 
            scec_txt = str(layer.get("scec", "")).strip()
            if scec_txt and scec_txt not in ("-99", ""):
                try:
                    scec_val = float(scec_txt)
                    if not (0 <= scec_val <= 99999):
                        QMessageBox.warning(self, "Invalid CEC",
                                            f"{lbl}: CEC must be between 0 and 99999.")
                        return
                    if not _dssat_decimal_ok(scec_txt):
                        QMessageBox.warning(self, "Invalid CEC",
                                            f"{lbl}: CEC integer part must be ≤ 3 digits.")
                        return
                except ValueError:
                    pass

            # Total Nitrogen: 0-20, accepts -99
            slni_txt = str(layer.get("slni", "")).strip()
            if slni_txt and slni_txt not in ("-99", ""):
                try:
                    slni_val = float(slni_txt)
                    if not (0 <= slni_val <= 20):
                        QMessageBox.warning(self, "Invalid Total Nitrogen",
                                            f"{lbl}: Total Nitrogen must be between 0 and 20.")
                        return
                except ValueError:
                    pass

            # More Inputs: all 0-999, accept -99
            _more_inputs = [
                ("slpa",  "Phosphorus isotherm A"),
                ("slpb",  "Phosphorus isotherm B"),
                ("caco3", "Calcium carbonate"),
                ("slal",  "Aluminum"),
                ("slke",  "Potassium exchangeable"),
                ("sadc",  "Nitrate adsorption factor"),
                ("slca",  "Calcium exchangeable"),
            ]
            for _key, _label in _more_inputs:
                _txt = str(layer.get(_key, "")).strip()
                if _txt and _txt not in ("-99", ""):
                    try:
                        _val = float(_txt)
                        if not (0 <= _val <= 999):
                            QMessageBox.warning(self, f"Invalid {_label}",
                                                f"{lbl}: {_label} must be between 0 and 999.")
                            return
                    except ValueError:
                        pass

            # Calculate/Edit soil parameters fields
            _calc_fields = [
                ("slll", "Lower Limit",                0, 9),
                ("sdul", "Drained Upper Limit",         0, 9),
                ("ssat", "Saturated Water Content",     0, 9),
                ("sbdm", "Bulk Density",                0, 2.65),
                ("ssks", "Sat. Hydraulic Conductivity", 0, 99),
                ("srgf", "Root Growth Factor",          0, 1),
            ]
            for _key, _label, _lo, _hi in _calc_fields:
                _txt = str(layer.get(_key, "")).strip()
                if _txt and _txt not in ("-99", ""):
                    try:
                        _val = float(_txt)
                        if not (_lo <= _val <= _hi):
                            QMessageBox.warning(self, f"Invalid {_label}",
                                                f"{lbl}: {_label} must be between {_lo} and {_hi}.")
                            return
                    except ValueError:
                        pass

        pid = self.currentProfile["code"] if self.currentProfile else ""

        # collect header information
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

        # stage everything for a future file save
        self._pendingSave = dict(
            sol_path     = Path(self.currentSolFile)
                           if self.currentSolFile else None,
            current_code = pid,
            kwargs       = kwargs,
        )

        QMessageBox.information(
            self, "Ready",
            "Changes are now staged in memory.\n"
            "Choose File ▸ Save when you’re ready to write them to disk."
        )
        self.ui.stackedWidget.setCurrentIndex(1)    # back to the first page

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