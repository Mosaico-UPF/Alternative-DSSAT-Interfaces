import sys
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

from sbuild import Ui_MainWindow
from profileList import Ui_Dialog, ProfileListDialog
from readSoilFile import read_profile, show_profiles
from createSoilFile import build_soil_file
from updateSoilFile import update_soil_file
from deleteSoilFile import delete_soil_profile
from hydrology import slope_from_cn

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
        self.ui.tableWidget.setSortingEnabled(False)
        self.tableCalc = self.ui.tableWidget_3
        self.ui.pushButton_4.setEnabled(False)
        self.ui.actionOpen.triggered.connect(self.openSolFile)
        self.ui.actionEdit_3.triggered.disconnect()
        self.ui.actionEdit_3.triggered.connect(self.openProfileList)
        self.ui.actionDelete_3.triggered.connect(self.askDeleteProfile)
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
            QMessageBox.warning(self, "Aviso", "Nenhum .SOL aberto.")
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
        cmap = {"BL": "Black", "BN": "Brown", "G": "Grey", "R": "Red", "Y": "Yellow"}
        self.ui.color_box.setCurrentText(cmap.get(data["color_code"], ""))

        # Drainage class (combo) --------------------------------------
        try:
            dr_val = float(data["drainage_rate"])
        except (TypeError, ValueError):
            dr_val = None
        self.ui.drainage_box.setCurrentText(drainage_class(dr_val))

        # Run-off potential & % slope ---------------------------------
        rc = float(data["runoff_curve"] or 0)
        if rc <= 0:
            self.ui.runoffPotential_box.setCurrentIndex(-1)
            self.ui.slope_line.clear()
        else:
            if   rc <= 60: txt_ro = "Lowest"
            elif rc <= 80: txt_ro = "Moderately Low"
            elif rc <= 90: txt_ro = "Moderately High"
            else:          txt_ro = "Highest"
            self.ui.runoffPotential_box.setCurrentText(txt_ro)
            slope_val = slope_from_cn(txt_ro, int(rc))
            self.ui.slope_line.setText("" if slope_val is None else str(slope_val))

        self.ui.fertilityFactor_line.setText(data["fertility_factor"])

        # === Surface-parameter widgets na aba “Calculate/Edit” =======
        # ajuste os nomes se seus QLineEdits forem diferentes
        self.ui.lineEdit.setText(data["runoff_curve"])       # SLRO
        self.ui.lineEdit_2.setText(data["albedo"])           # SALB
        self.ui.lineEdit_3.setText(data["drainage_rate"])    # SLDR

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
        self.fileStatusAction.setText(f"Working with file: {os.path.basename(file_name)}")

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
    def _write_profile(self, profile_id: str, sol_path: Optional[Path]) -> None:
        """
        Decide entre criar novo arquivo, anexar novo perfil ou atualizar perfil
        existente, de acordo com o estado atual da UI.
        """
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
            soil_data_source    = self.ui.soilData_line.text()         or "-99",
            soil_series_name    = self.ui.soilSeries_line.text()       or "-99",
            scs_family          = self.ui.soilClassification_line.text() or "-99",
            scom                = {"Black":"BL","Brown":"BN","Grey":"G",
                                "Red":"R","Yellow":"Y"}.get(self.ui.color_box.currentText(),"BN"),
        )

        if sol_path is None:             # 1) novo arquivo
            dest = QFileDialog.getSaveFileName(self,
                                            "Salvar novo arquivo .SOL",
                                            f"{profile_id}.SOL",
                                            "Arquivos DSSAT (*.SOL)")[0]
            if not dest:  # cancelado
                return
            build_soil_file(dest=dest, **kwargs)

        elif self.currentProfile is None:    # 2) arquivo aberto + sem perfil selecionado
            tmp = Path(sol_path).with_suffix(".SOL")
            build_soil_file(dest=tmp, **kwargs)       # gera bloco sozinho
            # anexa ao final preservando cabeçalho
            original = Path(sol_path).read_text(encoding="utf-8")
            new      = tmp.read_text(encoding="utf-8").splitlines()[2:]  # tira 2 linhas de cabeçalho
            with open(sol_path, "a", encoding="utf-8") as f:
                f.write("\n" + "\n".join(new))
            tmp.unlink()

        else:                               # 3) atualizar perfil existente
            update_soil_file(sol_path, self.currentProfile["code"], kwargs|{"layers":layers})
    # -----------------------------------------------------------------------
        
    def openProfileList(self):
        sol = self.getCurrentSolFile()
        if not sol or not Path(sol).exists():
            QMessageBox.warning(self, "Aviso", "Nenhum .SOL aberto.")
            return

        profiles = show_profiles(sol)
        dlg = ProfileListDialog(profiles, self)
        if dlg.exec_() == QDialog.Accepted and dlg.selected_profile:
            self.currentProfile = dlg.selected_profile
            assert self.currentProfile is not None, "Selecione um perfil primeiro"
            self.populateFieldsFromProfile(self.currentProfile)

    def writeSolFile(self):
        sol = self.getCurrentSolFile()
        if not sol or not Path(sol).exists():
            QMessageBox.warning(self, "Aviso", "Nenhum .SOL aberto para edição.")
            return
        assert self.currentProfile, "Selecione um perfil primeiro"
        self.populateFieldsFromProfile(self.currentProfile)

        code = self.currentProfile["code"]
        data = {
            "country":             self.ui.country_line.text(),
            "institute_code":      self.ui.instituteCode_line.text(),
            "site_name":           self.ui.siteName_line.text(),
            "latitude":            self.ui.latitude_line.text(),
            "longitude":           self.ui.longitude_line.text(),
            "soil_data_source":    self.ui.soilData_line.text(),
            "soil_series":         self.ui.soilSeries_line.text(),
            "soil_classification": self.ui.soilClassification_line.text(),
            "layers": [],
        }
        layers = []
        for r in range(self.ui.tableWidget.rowCount()):
            cell0 = self.ui.tableWidget.item(r, 0)
            cell1 = self.ui.tableWidget.item(r, 1)
            layers.append({
                "depth":   cell0.text() if cell0 else "",
                "texture": cell1.text() if cell1 else "",
                "color":            self.ui.color_box.currentText(),
                "drainage":         self.ui.drainage_box.currentText(),
                "runoff_potential": self.ui.runoffPotential_box.currentText()
            })
        data["layers"] = layers
        try:
            update_soil_file(sol, code, data)
            QMessageBox.information(self, "OK",
                f"Perfil de solo '{code}' atualizado com sucesso em «{sol}».")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao salvar:\n{e}")
    
    # ---------------------------------------------------------------
    def askDeleteProfile(self):                                     # ADD
        """Abre a lista de perfis, pergunta qual excluir e faz a remoção."""
        sol = self.getCurrentSolFile()
        if not sol or not Path(sol).exists():
            QMessageBox.warning(self, "Aviso", "Nenhum .SOL aberto.")
            return

        profiles = show_profiles(sol)
        if not profiles:
            QMessageBox.information(self, "Aviso", "Arquivo sem perfis.")
            return

        # mesmo diálogo usado em editar
        dlg = ProfileListDialog(profiles, self)
        dlg.setWindowTitle("Escolha o perfil para EXCLUIR")
        if dlg.exec_() != QDialog.Accepted or not dlg.selected_profile:
            return

        code = dlg.selected_profile["code"]
        if QMessageBox.question(
                self,
                "Confirmar exclusão",
                f"Remover o perfil '{code}' de {os.path.basename(sol)}?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No) != QMessageBox.Yes:
            return

        try:
            delete_soil_profile(sol, code)
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao excluir:\n{e}")
            return

        # limpa UI se o perfil exibido era o apagado
        if self.currentProfile and self.currentProfile.get("code") == code:
            self.currentProfile = None
            self.cleanFields()

        QMessageBox.information(self, "OK", f"Perfil '{code}' removido.")
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

    def deleteLayer(self):
        sm = self.ui.tableWidget.selectionModel()
        if sm is None:
            return
        rows = [idx.row() for idx in sm.selectedRows()]

        if rows:  # Se houver linhas selecionadas
            rows.sort(reverse=True)
            for row in rows:
                self.ui.tableWidget.removeRow(row)
                self.ui.tableWidget_2.removeRow(row)
        else:  # Nenhuma linha selecionada — remove a última
            last_row = self.ui.tableWidget.rowCount() - 1
            if last_row >= 0:
                self.ui.tableWidget.removeRow(last_row)
                self.ui.tableWidget_2.removeRow(last_row)

        self.checkButton()


    def goToFinalPage(self):
        self.ui.stackedWidget.setCurrentIndex(3)
    
    def goToPage2(self):
        self.ui.stackedWidget.setCurrentIndex(1)

    def goForward(self):
        current_index = self.ui.stackedWidget.currentIndex()
        self.ui.stackedWidget.setCurrentIndex(current_index + 1)

    def goBack(self):
        current_index = self.ui.stackedWidget.currentIndex()
        self.ui.stackedWidget.setCurrentIndex(current_index - 1)

    def handlePage0Ok(self):
        country = self.ui.country_line.text()
        institute_code = self.ui.instituteCode_line.text()
        site_name = self.ui.siteName_line.text()
        latitude = self.ui.latitude_line.text()
        longitude = self.ui.longitude_line.text()
        soil_data_source = self.ui.soilData_line.text()
        soil_series = self.ui.soilSeries_line.text()
        soil_classification = self.ui.soilClassification_line.text()
        """with open("output.txt", "w", encoding="utf-8") as f:
            f.write("General Information:\n")
            f.write(f"Country: {country}\n")
            f.write(f"Institute Code: {institute_code}\n")
            f.write(f"Site Name: {site_name}\n")
            f.write(f"Latitude: {latitude}\n")
            f.write(f"Longitude: {longitude}\n")
            f.write(f"Soil Data Source: {soil_data_source}\n")
            f.write(f"Soil Series Name: {soil_series}\n")
            f.write(f"Soil Classification: {soil_classification}\n\n")
            f.write("--- End of Page 0 Data ---\n") """
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
        Último botão OK.
        Decide criar / anexar / atualizar perfil *.SOL* conforme:
            1) nenhum arquivo aberto  → criar novo .SOL
            2) arquivo aberto sem perfil selecionado → anexar
            3) arquivo + perfil selecionado → atualizar
        """
        sol_path = Path(self.currentSolFile) if self.currentSolFile else None

        # Pede ID do perfil (10 chars)
        pid, ok = QtWidgets.QInputDialog.getText(
            self, "Profile ID",
            "Informe o código do novo perfil (10 caracteres):",
            text=self.currentProfile["code"] if self.currentProfile else "")
        if not ok:
            return
        pid = pid.strip().upper()
        if len(pid) != 10:
            QMessageBox.warning(self, "Erro", "O código deve ter exatamente 10 caracteres.")
            return

        try:
            self._write_profile(pid, sol_path)
        except Exception as e:
            QMessageBox.critical(self, "Falha", f"Não foi possível gravar o perfil:\n{e}")
            return

        QMessageBox.information(self, "Pronto!", "Perfil gravado com sucesso.")
        self.ui.stackedWidget.setCurrentIndex(0)      # volta p/ tela inicial

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