import sys
import os
import json
import requests
import subprocess
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import (QApplication, QMainWindow, QListWidgetItem, QFileDialog, 
                             QMessageBox, QVBoxLayout, QLabel, QListWidget, QPushButton, 
                             QWidget, QCheckBox, QGroupBox, QScrollArea, QSizePolicy, 
                             QDialog, QRadioButton, QButtonGroup, QFormLayout, QTextEdit)
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
from collections import defaultdict
from common_functions import plot_graph, print_graph, export_data_to_txt_scatter, export_data_to_excel_scatter, select_directory, load_files, list_files, preview_file, open_file, graph_scatter, set_new_window, close_evaluate
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

qt_plugin_path = os.path.join(os.path.dirname(sys.executable), 'Lib', 'site-packages', 'PyQt5', 'Qt', 'plugins', 'platforms')
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = qt_plugin_path

class GraphWindow(QWidget):
    def export_variables_to_txt(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Variables to TXT", "", "Text Files (*.txt);;All Files (*)", options=options)
        if file_path:
            max_days = max(len(dataset['y']) for dataset in self.plot_data) 

            df = pd.DataFrame({'Day': range(1, max_days + 1)})

            run_names = defaultdict(list)

            for dataset in self.plot_data:
                label = dataset.get('label', 'No label')
                values = dataset.get('y', [])

                values += [None] * (max_days - len(values))  
                
                run = label.split('(')[-1].strip(')')  
                run_names[run].append(label)  
                
                df[label] = values

           
            new_columns = {}
            for i, run in enumerate(run_names.keys(), start=1):
                for j, var_name in enumerate(run_names[run]):
                    new_columns[var_name] = f"{var_name.split(' ')[0]} (Run {i})"  

            df.rename(columns=new_columns, inplace=True)

           
            column_widths = {col: max(len(col), df[col].astype(str).map(len).max()) for col in df.columns}

           
            with open(file_path, 'w') as f:
                header = '\t'.join(col.ljust(column_widths[col]) for col in df.columns)
                f.write(header + '\n')

            
                for index, row in df.iterrows():
                    line = '\t'.join(str(item).ljust(column_widths[col]) if item is not None else ' ' * column_widths[col] for col, item in zip(df.columns, row))
                    f.write(line + '\n')

    def export_data_to_excel(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Data to Excel", "", "Excel Files (*.xlsx);;All Files (*)", options=options)
        if file_path:
            with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
                df = pd.DataFrame()
                for dataset in self.plot_data:
                    label = dataset.get('label', 'No label')
                    values = dataset.get('y', [])
                    df[label] = values

                df.to_excel(writer, sheet_name='Data', index=False, startrow=1)  
                workbook = writer.book
                worksheet = writer.sheets['Data']

                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value)  

                chart_sheet = workbook.add_worksheet('Charts')

                chart = workbook.add_chart({'type': 'line'})

                for i, col in enumerate(df.columns):
                    chart.add_series({
                        'name': col,
                        'values': f'Data!${chr(65 + i)}$2:${chr(65 + i)}${len(df) + 1}'  
                    })

                chart.set_title({'name': 'Graph Title'})  
                chart.set_x_axis({'name': 'X-axis'})  
                chart.set_y_axis({'name': 'Y-axis'})  

                chart_sheet.insert_chart('B2', chart, {'x_offset': 25, 'y_offset': 10, 'x_scale': 2, 'y_scale': 1.5})

                for i in range(len(df.columns)):
                    chart_sheet.set_column(i, i, 0)  
    
class OptionsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Options")
        self.setGeometry(200, 200, 300, 200)
        self.plot_type = "evaluate"

        layout = QFormLayout()
        self.time_series_radio = QRadioButton("Time Series")
        self.scatter_plot_radio = QRadioButton("Scatter Plot")
        self.scatter_plot_radio.setChecked(False)
        self.time_series_radio.setChecked(True)

        self.plot_type_group = QButtonGroup()
        self.plot_type_group.addButton(self.time_series_radio)
        self.plot_type_group.addButton(self.scatter_plot_radio)

        layout.addRow("Plot Type:", self.time_series_radio)
        layout.addRow("", self.scatter_plot_radio)
        self.apply_button = QPushButton("Apply", self)
        self.apply_button.clicked.connect(self.apply)
        layout.addWidget(self.apply_button)

        self.setLayout(layout)

    def apply(self):
        plot_type = self.get_plot_type()
        close_evaluate(self.parent()) 

        if plot_type == "time series":
            from time_series import TimeSeriesWindow
            self.open_new_window(TimeSeriesWindow)
        elif plot_type == "scatter plot":
            from scatter_plot import ScatterPlotWindow
            self.open_new_window(ScatterPlotWindow)
        self.close()  

    def get_plot_type(self):
        return "scatter plot" if self.scatter_plot_radio.isChecked() else "time series"

    def open_new_window(self, window_class):
        self.parent().open_window(window_class)

    def get_plot_type(self):
        if self.scatter_plot_radio.isChecked():
            return "scatter plot"
        else:
            return "time series"
        
    def redirect_to_file(self, file_name):
        try:
            if os.path.exists(file_name):
                subprocess.run(["python", file_name])
            else:
                QMessageBox.warning(self, "Error", f"File {file_name} not found.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error opening file {file_name}: {str(e)}")

        
class EvaluateWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DSSAT Output Viewer - Evaluate")
        self.setGeometry(100, 100, 1200, 800)

        self.current_window = None
       
        self.centralwidget = QWidget(self)
        self.setCentralWidget(self.centralwidget)
        self.main_layout = QVBoxLayout(self.centralwidget)

       
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area_widget = QWidget()
        self.scroll_area.setWidget(self.scroll_area_widget)
        self.scroll_area_layout = QVBoxLayout(self.scroll_area_widget)
        self.main_layout.addWidget(self.scroll_area)

        self.label = QLabel("Select a evaluate.OUT file:", self)
        self.scroll_area_layout.addWidget(self.label)

        self.listWidget = QListWidget(self)
        self.scroll_area_layout.addWidget(self.listWidget)


        self.select_button = QPushButton("Select a directory", self)
        self.scroll_area_layout.addWidget(self.select_button)
        self.select_button.clicked.connect(self.select_directory)

        self.preview_button = QPushButton("Preview the selected file", self)
        self.scroll_area_layout.addWidget(self.preview_button)
        self.preview_button.clicked.connect(self.preview_file)

        self.open_button = QPushButton("Open the selected file", self)
        self.scroll_area_layout.addWidget(self.open_button)
        self.open_button.clicked.connect(self.open_file)

        self.variables_group = QGroupBox("Select variables")
        self.variables_layout = QVBoxLayout()
        self.variables_group.setLayout(self.variables_layout)
        self.scroll_area_layout.addWidget(self.variables_group)

        
        self.select_all_vars_button = QPushButton("Select All Variables", self)
        self.clear_all_vars_button = QPushButton("Clear All Variables", self)
        self.scroll_area_layout.addWidget(self.select_all_vars_button)
        self.scroll_area_layout.addWidget(self.clear_all_vars_button)
        
        self.select_all_vars_button.clicked.connect(self.select_all_vars)
        self.clear_all_vars_button.clicked.connect(self.clear_all_vars)

        self.plot_button = QPushButton("Create and display a graph", self)
        self.scroll_area_layout.addWidget(self.plot_button)
        self.plot_button.clicked.connect(self.plot_evaluate_data)

        self.options_button = QPushButton("Options", self)
        self.scroll_area_layout.addWidget(self.options_button)
        self.options_button.clicked.connect(self.show_options_dialog)

        self.default_directory = "C:/DSSAT48"
        self.current_directory = self.default_directory
        self.file_extension = ".OUT"
        self.data = []

        self.plot_type = "time series"  
        self.show()
    
    def closeEvent(self, event):
        event.accept() 
  
    def open_window(self, window_class, *args):
        if self.current_window is not None:
            self.current_window.close()
        self.current_window = window_class(*args) 
        self.current_window.show()

    def show_options_dialog(self):
        dialog = OptionsDialog(self)
        dialog.show() 

    def load_evaluate_file(self, file_path):
        with open(file_path, 'r') as file:
            lines = file.readlines()

        header_line = next(line for line in lines if line.startswith('@'))
        columns = header_line[1:].split()
        
        print("Header columns:", columns)

        data_lines = [line for line in lines if not line.startswith('*') and not line.startswith('@')]

        data = []
        for line in data_lines:
            values = line.split()
            entry = {col: val for col, val in zip(columns, values)}
            data.append(entry)

        print("Raw processed data:", data)

        df = pd.DataFrame(data)

        numeric_cols = df.columns.difference(['RUN', 'EXCODE', 'TN', 'RN', 'CR'])
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')

        print("DataFrame columns after processing:", df.columns)

        return df
   
    def show_options_dialog(self):
        dialog = OptionsDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.plot_type = dialog.get_plot_type()

    def select_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Directory", self.current_directory)
        if directory:
            self.current_directory = directory
            self.load_files(directory)

    def load_files(self, directory):
        if not os.path.exists(directory):
            QMessageBox.warning(self, "Warning!", "Directory not found")
            self.listWidget.clear()
            return
        self.list_files(directory, self.file_extension)
                
    def list_files(self, directory, extension):
        self.listWidget.clear()
        files_found = False
        for file_name in os.listdir(directory):
            if file_name.upper().endswith(extension):
                files_found = True
                file_path = os.path.join(directory, file_name)
                item = QListWidgetItem(file_name)
                item.setData(1, file_path)
                self.listWidget.addItem(item)
        if not files_found:
            self.listWidget.addItem("No files found")

    def preview_file(self):
        current_item = self.listWidget.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning!", "No file selected")
            return

        file_path = current_item.data(1)
        
        try:
            with open(file_path, 'r') as file:
                file_content = file.read()
            
            
            preview_dialog = QDialog(self)
            preview_dialog.setWindowTitle("Preview of " + current_item.text())
            preview_dialog.setGeometry(200, 200, 600, 400)

            text_edit = QTextEdit(preview_dialog)
            text_edit.setReadOnly(True)
            text_edit.setPlainText(file_content)
            
            layout = QVBoxLayout()
            layout.addWidget(text_edit)
            preview_dialog.setLayout(layout)
            
            preview_dialog.exec_()

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not preview the file: {str(e)}")

    def open_file(self):
        current_item = self.listWidget.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning!", "No file selected")
            return

        file_name = current_item.text()
        file_path = current_item.data(1)

        crop_name = os.path.basename(self.current_directory)
        file_name_for_api = file_name

        try:
            url = f"http://localhost:3000/api/out/{crop_name}/{file_name_for_api}"
            response = requests.get(url)
            response.raise_for_status()
            self.data = response.json()

            self.processed_data = [entry for entry in self.data if 'RUN' not in entry]

            print("Processed data:", self.processed_data)

            self.display_data()
        except requests.RequestException as e:
            QMessageBox.warning(self, "Error", f"Error accessing the API: {str(e)}")
            
    def display_data(self):
        for entry in self.processed_data:
            if isinstance(entry, dict):  
                for key in entry.keys():
                    print(f"{key}: {entry[key]}")
            else:
                print(f"Skipping entry, not a dictionary: {entry}")
                
    def select_all_vars(self):
        for checkbox in self.variables_group.findChildren(QCheckBox):
            checkbox.setChecked(True)

    def clear_all_vars(self):
        for checkbox in self.variables_group.findChildren(QCheckBox):
            checkbox.setChecked(False)

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
  
    def plot_evaluate_data(self):
        selected_vars = [cb.text() for cb in self.variables_group.findChildren(QCheckBox) if cb.isChecked()]
        
        if not selected_vars:
            QMessageBox.warning(self, "Warning!", "No variables selected for the graph.")
            return
        
        if not self.data or not all(var in self.data for var in selected_vars):
            QMessageBox.warning(self, "Warning!", "Data not loaded or selected variables are not available.")
            return
        
        plt.figure(figsize=(10, 6))
        for var in selected_vars:
            plt.plot(self.data[var], label=var)  
        
        plt.xlabel("Index")
        plt.ylabel("Values")
        plt.title("Evaluate.OUT Graph")
        plt.legend()
        plt.grid(True)
        plt.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainWindow = EvaluateWindow()
    sys.exit(app.exec_())
