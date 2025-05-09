import sys
from PyQt5 import QtWidgets
from sbuild import Ui_MainWindow
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QComboBox
from PyQt5.QtCore import Qt, QEvent

class MainWindow(QtWidgets.QMainWindow):
    
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.buttonBox.accepted.connect(self.handlePage0Ok)
        self.ui.buttonBox.rejected.connect(self.handlePage0Cancel)
        self.ui.buttonBox_3.accepted.connect(self.goToFinalPage)
        self.ui.buttonBox_3.rejected.connect(self.goBack)
        self.ui.buttonBox_2.accepted.connect(self.goBack)
        self.ui.buttonBox_2.rejected.connect(self.goBack)
        self.ui.Finish.accepted.connect(self.handlePage3Ok)
        self.ui.Finish.rejected.connect(self.goToPage2)
        self.ui.pushButton_2.clicked.connect(self.goForward)
        self.ui.pushButton_3.clicked.connect(self.addLayer)
        self.ui.pushButton_4.clicked.connect(self.deleteLayer)
        self.ui.tableWidget.setSortingEnabled(False)
        self.ui.pushButton_4.setEnabled(False)
        self.ui.actionOpen.triggered.connect(self.openSoilFile)
        self._prepare_combo(self.ui.color_box)
        self._prepare_combo(self.ui.drainage_box)
        self._prepare_combo(self.ui.runoffPotential_box)

    def addLayer(self):
        """Adiciona uma nova linha (row) ao final da tabela."""
        current_rows = self.ui.tableWidget.rowCount()
        self.ui.tableWidget.insertRow(current_rows)
        more_rows = self.ui.tableWidget_2.rowCount()
        self.ui.tableWidget_2.insertRow(more_rows)
        self.checkButton()

    def _prepare_combo(self, combo: QComboBox):
        combo.setEditable(False)        # ← volta ao comportamento padrão
        combo.setInsertPolicy(QComboBox.NoInsert)   # (se quiser manter)
        combo.setCurrentIndex(-1)       # nenhum item selecionado → caixa vazia

    def checkButton(self):
        has_rows = self.ui.tableWidget.rowCount() > 1
        self.ui.pushButton_4.setEnabled(has_rows)

    def deleteLayer(self):
        selected_indexes = self.ui.tableWidget.selectionModel().selectedRows()
        rows = [index.row() for index in selected_indexes]

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
        institute_code = self.ui.institudeCode_line.text()
        site_name = self.ui.siteName_line.text()
        latitude = self.ui.latitude_line.text()
        longitude = self.ui.longitude_line.text()
        soil_data_source = self.ui.soilData_line.text()
        soil_series = self.ui.soilSeries_line.text()
        soil_classification = self.ui.soilClassification_line.text()
        with open("output.txt", "w", encoding="utf-8") as f:
            f.write("General Information:\n")
            f.write(f"Country: {country}\n")
            f.write(f"Institute Code: {institute_code}\n")
            f.write(f"Site Name: {site_name}\n")
            f.write(f"Latitude: {latitude}\n")
            f.write(f"Longitude: {longitude}\n")
            f.write(f"Soil Data Source: {soil_data_source}\n")
            f.write(f"Soil Series Name: {soil_series}\n")
            f.write(f"Soil Classification: {soil_classification}\n\n")
            f.write("--- End of Page 0 Data ---\n")
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
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar arquivo .SOL",
            "MEUSOLO.SOL",
            "Arquivos DSSAT (*.SOL);;Todos os arquivos (*)"
        )
        if not file_path:
            return  # usuário cancelou

        try:
            self.writeSolFile(file_path)
            QMessageBox.information(self, "Concluído", "Arquivo salvo com sucesso!")
            self.ui.stackedWidget.setCurrentIndex(0)
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao salvar:\n{e}")


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
                # Aqui você pode fazer o que quiser com o conteúdo, como carregar na interface
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Não foi possível abrir o arquivo:\n{str(e)}")

if __name__ == "__main__":
    import sys
    from logic import MainWindow
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
