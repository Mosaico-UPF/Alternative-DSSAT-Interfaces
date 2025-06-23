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

    # Table in crescent values
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
        if dr_val <= val + 1e-6:      # First value ≥ SLDR
            return label
    return "Very Excessive"           # SLDR bigger than 0.95

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
        assert mb is not None, "menuBar wasn't initialized"
        mb.addAction(self.fileStatusAction)
        mb.setStyleSheet("QMenuBar::item:disabled { color: black; }")

    def addLayer(self) -> None:
        """Adiciona uma nova camada (+ 5 cm) sincronizando TODAS as grades."""
        """Adds a new layer (+ 5 cm) synchronizing all the grids"""
        tw1 = self.ui.tableWidget          # main grid
        tw2 = self.ui.tableWidget_2        # “More inputs”
        tw3 = self.tableCalc               # “Calculate/Edit Soil Parameters”
        r   = tw1.rowCount()               # indexes for the new line

        # ── depth -------------------------------------------------------
        if r == 0:
            depth_val = 5
        else:
            try:
                depth_val = int(tw1.item(r - 1, 0).text()) + 5
            except Exception:
                depth_val = 5

        # ── inserts line in the three tables -------------------------------------
        for tw in (tw1, tw2, tw3):
            tw.insertRow(r)
            tw.setItem(r, 0, QTableWidgetItem(str(depth_val)))

        # column “Master horizon” (main grid) with default –99
        tw1.setItem(r, 1, QTableWidgetItem("-99"))

        self.checkButton()

    def preview(self):
        # TODO
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
        # ─── .SOL path + code ─────────────────────────────────
        sol0 = self.getCurrentSolFile()
        if sol0 is None:
            QMessageBox.warning(self, "Warning!", "No .SOL file opened")
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
        # adjust the names accordingly
        self.ui.lineEdit.setText(data["runoff_curve"])       # SLRO
        self.ui.lineEdit_2.setText(data["albedo"])           # SALB
        self.ui.lineEdit_3.setText(data["drainage_rate"])    # SLDR

        # === Layers tables (main + more-inputs + calculate) =====
        tw_main = self.ui.tableWidget
        tw_more = self.ui.tableWidget_2
        tw_calc = self.tableCalc          # tab grid “Calculate/Edit”

        # clears all
        for tw in (tw_main, tw_more, tw_calc):
            tw.setRowCount(0)

        # exact order of the columns in the grid -----------------------
        main_keys = ["depth", "texture", "clay", "silt",
                    "stones", "oc", "ph", "cec", "tn"]

        # grade de cálculo – todas as colunas já existentes no .ui
        # Calc Grid - All existing rows from the .ui
        calc_keys = ["depth", "clay", "silt", "stones",
                    "lll", "dul", "sat", "bd", "ksat", "srgf"]

        for layer in data.get("layers", []):
            r = tw_main.rowCount()

            # creates lines in the three grids
            for tw in (tw_main, tw_more, tw_calc):
                tw.insertRow(r)

            # ── main grid ---------------------------------------
            for c, k in enumerate(main_keys):
                tw_main.setItem(r, c, QTableWidgetItem(layer.get(k, "")))

            # ── more-inputs: only depth (mirrored) ----------
            tw_more.setItem(r, 0, QTableWidgetItem(layer.get("depth", "")))
 
            # ── Calc Grid (all the parameters) ----------
            for c, k in enumerate(calc_keys):
                tw_calc.setItem(r, c, QTableWidgetItem(layer.get(k, "")))

        self.checkButton()

    def openSolFile(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Opens the .SOL for reading the profiles",
            "",
            "DSSAT Files (*.SOL);;All the files (*)",
            options=options
        )
        if file_name:
            self.setCurrentSolFile(file_name)
            self.fileStatusAction.setText(os.path.basename(file_name))
        if not file_name:
            return  # User cancelled
        else: 
            self.setCurrentSolFile(file_name)
        try:
            # Calls show_profiles to extract the profiles from the selected file
            profiles = show_profiles(file_name)  # Returns a list of dictionaries

            if profiles:
                # Extract the code from each profile for exibition
                message = "\n\n".join(
                f"Perfil: {profile['code']}\n{profile['content']}" for profile in profiles
            )
                #QMessageBox.information(self, "Soil profiles", f"Found profiles:\n{message}")
            else:
                QMessageBox.information(self, "Soil Profiles", "No profile found in the file.")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao ler o arquivo:\n{e}")
    
    def setCurrentSolFile(self, file_name: str):
        self.currentSolFile = file_name
        self.fileStatusAction.setText(f"Working with file: {os.path.basename(file_name)}")

    def getCurrentSolFile(self) -> Optional[str]:
        return self.currentSolFile
    


    def _collect_layers(self) -> list[dict]:
        """Reads all the lines from the main grid and returns [{SLB, SLLL, ...}...]."""
        tw_main = self.ui.tableWidget
        tw_calc = self.tableCalc

        layers: list[dict] = []
        for r in range(tw_main.rowCount()):
            try:  # depth isn't optional
                slb = int(tw_main.item(r, 0).text())
            except Exception:
                continue     # skips empty lines

            layer = {
                # basics (main grid) -------------------------------
                "slb":  slb,
                "slmh":   tw_main.item(r, 1).text()  if tw_main.item(r, 1)  else "-99",
                "slcl":   tw_main.item(r, 2).text()  if tw_main.item(r, 2)  else -99,
                "slsi":   tw_main.item(r, 3).text()  if tw_main.item(r, 3)  else -99,
                "slcf":   tw_main.item(r, 4).text()  if tw_main.item(r, 4)  else -99,
                "sloc":   tw_main.item(r, 5).text()  if tw_main.item(r, 5)  else -99,
                "slhw":   tw_main.item(r, 6).text()  if tw_main.item(r, 6)  else -99,
                "scec":   tw_main.item(r, 7).text()  if tw_main.item(r, 7)  else -99,
                "slni":   tw_main.item(r, 8).text()  if tw_main.item(r, 8)  else -99,
                # hydraulics (main grid) ----------------------------
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
        Decides between creating a new file, anexing a new profile or updating the existing 
        profile, according to the current UI state

        """
        layers = self._collect_layers()
        if not layers:
            raise ValueError("Tabela de camadas vazia.")

        # --- Header ---------------------------------------------------
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

        if sol_path is None:             # 1) new file
            dest = QFileDialog.getSaveFileName(self,
                                            "Save new .SOL file",
                                            f"{profile_id}.SOL",
                                            "DSSAT Files (*.SOL)")[0]
            if not dest:  # canceled
                return
            build_soil_file(dest=dest, **kwargs)

        elif self.currentProfile is None:    # 2) opened file + no selected profile
            tmp = Path(sol_path).with_suffix(".SOL")
            build_soil_file(dest=tmp, **kwargs)       # generates the block alone
            # anexes at the end, maintaining the header
            original = Path(sol_path).read_text(encoding="utf-8")
            new      = tmp.read_text(encoding="utf-8").splitlines()[2:]  # removes 2 header lines
            with open(sol_path, "a", encoding="utf-8") as f:
                f.write("\n" + "\n".join(new))
            tmp.unlink()

        else:                               # 3) update the existing profile
            update_soil_file(sol_path, self.currentProfile["code"], kwargs|{"layers":layers})
    # -----------------------------------------------------------------------
        
    def openProfileList(self):
        sol = self.getCurrentSolFile()
        if not sol or not Path(sol).exists():
            QMessageBox.warning(self, "Warning", "No .SOL opened.")
            return

        profiles = show_profiles(sol)
        dlg = ProfileListDialog(profiles, self)
        if dlg.exec_() == QDialog.Accepted and dlg.selected_profile:
            self.currentProfile = dlg.selected_profile
            assert self.currentProfile is not None, "Select a profile first"
            self.populateFieldsFromProfile(self.currentProfile)

    def writeSolFile(self):
        sol = self.getCurrentSolFile()
        if not sol or not Path(sol).exists():
            QMessageBox.warning(self, "Warning", "No .SOL opened for editing.")
            return
        assert self.currentProfile, "First, select a profile"
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
                f"Soil profile '{code}' Updated successfully «{sol}».")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed saving:\n{e}")
    
    # ---------------------------------------------------------------
    def askDeleteProfile(self):                                     # ADD
        """Opens the profile list, asks which one should be excluded and removes"""
        sol = self.getCurrentSolFile()
        if not sol or not Path(sol).exists():
            QMessageBox.warning(self, "Warning!", "No .SOL opened.")
            return

        profiles = show_profiles(sol)
        if not profiles:
            QMessageBox.information(self, "Warning!", "File opened without profiles.")
            return

        # Using the same dialog as Edit
        dlg = ProfileListDialog(profiles, self)
        dlg.setWindowTitle("Select a file to delete")
        if dlg.exec_() != QDialog.Accepted or not dlg.selected_profile:
            return

        code = dlg.selected_profile["code"]
        if QMessageBox.question(
                self,
                "Confirm deletion",
                f"Remove the profile '{code}' from {os.path.basename(sol)}?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No) != QMessageBox.Yes:
            return

        try:
            delete_soil_profile(sol, code)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete:\n{e}")
            return

        # Clears the UI if the profile exibited was the deleted
        if self.currentProfile and self.currentProfile.get("code") == code:
            self.currentProfile = None
            self.cleanFields()

        QMessageBox.information(self, "OK", f"Profile '{code}' was deleted.")
    # ---------------------------------------------------------------

    def _prepare_combo(self, combo: QComboBox):
        combo.setEditable(False)       
        combo.setInsertPolicy(QComboBox.NoInsert)   
        combo.setCurrentIndex(-1)       # no selected item -> Empty box

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

        if rows:  # If there are selected lines
            rows.sort(reverse=True)
            for row in rows:
                self.ui.tableWidget.removeRow(row)
                self.ui.tableWidget_2.removeRow(row)
        else:  # No line selected, removes the last
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
        Last ok button.
        Decides create / annex / update profile *.SOL* according:
            1) no opened file  → create new .SOL
            2) file opened, no selected profile → annex
            3) file + selected profile → update
        """
        sol_path = Path(self.currentSolFile) if self.currentSolFile else None

        # Asks for profile id (10 Chars)
        pid, ok = QtWidgets.QInputDialog.getText(
            self, "Profile ID",
            "Inform the new profile ID (10 Characters):",
            text=self.currentProfile["code"] if self.currentProfile else "")
        if not ok:
            return
        pid = pid.strip().upper()
        if len(pid) != 10:
            QMessageBox.warning(self, "Error", "The code must have 10 characters.")
            return

        try:
            self._write_profile(pid, sol_path)
        except Exception as e:
            QMessageBox.critical(self, "Falha", f"Não foi possível gravar o perfil:\n{e}")
            return

        QMessageBox.information(self, "Pronto!", "Perfil gravado com sucesso.")
        self.ui.stackedWidget.setCurrentIndex(0)      # returns to main screend

    def handlePage3Cancel(self):
        self.ui.stackedWidget.setCurrentIndex(2)
    
    def openSoilFile(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Open the .SOL file", "", "DSSAT files (*.SOL);;All the files (*)", options=options)
    
        if file_name:
            try:
                with open(file_name, "r", encoding="utf-8") as f:
                    content = f.read()
                    QMessageBox.information(self, "Opened file", f"File content:\n\n{content[:500]}...\n\n(Truncated)")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"It was not possible to open the file:\n{str(e)}")

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