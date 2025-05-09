import sys
import os
import subprocess
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import (QApplication, QMainWindow, QListWidgetItem, QFileDialog, 
                             QMessageBox, QVBoxLayout, QLabel, QListWidget, QPushButton, 
                             QWidget, QCheckBox, QGroupBox, QScrollArea, QSizePolicy, 
                             QDialog, QRadioButton, QButtonGroup, QFormLayout, QAbstractItemView)
from common_functions import plot_graph, print_graph, export_data_to_txt_scatter, export_data_to_excel_scatter, select_directory, load_files, list_files, preview_file, open_file, graph_scatter, set_new_window, close_scatter_plot
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

qt_plugin_path = os.path.join(os.path.dirname(sys.executable), 'Lib', 'site-packages', 'PyQt5', 'Qt', 'plugins', 'platforms')
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = qt_plugin_path

class OptionsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Options")
        self.setGeometry(200, 200, 300, 200)
        self.plot_type = "scatter plot"

        layout = QFormLayout()
        self.evaluate_file_radio= QRadioButton("Evaluate File")
        self.time_series_radio = QRadioButton("Time Series")
        self.evaluate_file_radio.setChecked(False)
        self.time_series_radio.setChecked(True)

        self.plot_type_group = QButtonGroup()
        self.plot_type_group.addButton(self.time_series_radio)
        self.plot_type_group.addButton(self.evaluate_file_radio)

        layout.addRow("Plot Type:", self.time_series_radio)
        layout.addRow("", self.evaluate_file_radio)
        self.apply_button = QPushButton("Apply", self)
        self.apply_button.clicked.connect(self.apply)
        layout.addWidget(self.apply_button)

        self.setLayout(layout)

    def apply(self):
        plot_type = self.get_plot_type()
        close_scatter_plot(self.parent())

        if plot_type == "time series":
            from time_series import TimeSeriesWindow
            self.time_series_window = TimeSeriesWindow()  
            self.time_series_window.show()
        elif plot_type == "evaluate file":
            from evaluate import EvaluateWindow
            self.evaluate_window = EvaluateWindow()
            self.evaluate_window.show()
            
    def get_plot_type(self):
        if self.time_series_radio.isChecked():
            return "time series"
        else:
            return "evaluate file"

    def redirect_to_file(self, file_name):
        try:
            if os.path.exists(file_name):
                subprocess.run(["python", file_name])
            else:
                QMessageBox.warning(self, "Error", f"File {file_name} not found.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error opening file {file_name}: {str(e)}")

class GraphWindow(QWidget):
    def __init__(self, plot_data, plot_type, data, variables_group, runs_group):
        super().__init__()
        self.data = data   
        self.plot_data = plot_data
        self.variables_group = variables_group
        self.runs_group = runs_group
        self.setWindowTitle("Graph Window")
        self.setGeometry(100, 100, 800, 600)
        self.figure = plt.Figure()
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.canvas.updateGeometry()

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)

        plot_graph(self.figure, plot_data, plot_type)
      
        self.print_button = QPushButton("Print Graph")
        self.export_txt_button = QPushButton("Export Variables to TXT")
        self.export_excel_button = QPushButton("Export Data & Graph to Excel")

        layout.addWidget(self.print_button)
        layout.addWidget(self.export_txt_button)
        layout.addWidget(self.export_excel_button)

        self.print_button.clicked.connect(lambda: print_graph(self.canvas, self))
        self.export_txt_button.clicked.connect(lambda: export_data_to_txt_scatter(self.plot_data, self))
        self.export_excel_button.clicked.connect(lambda: export_data_to_excel_scatter(self.plot_data, self))
            
class ScatterPlotWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DSSAT Output Viewer - Scatter Plot")
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

        self.label = QLabel("Select a .OUT file:", self)
        self.scroll_area_layout.addWidget(self.label)

        self.listWidget = QListWidget(self)
        self.scroll_area_layout.addWidget(self.listWidget)
        self.listWidget.setSelectionMode(QAbstractItemView.MultiSelection)

        self.select_button = QPushButton("Select a directory", self)
        self.scroll_area_layout.addWidget(self.select_button)
        self.select_button.clicked.connect(self.select_directory)

        self.preview_button = QPushButton("Preview the selected file", self)
        self.scroll_area_layout.addWidget(self.preview_button)
        self.preview_button.clicked.connect(self.preview_file)

        self.open_button = QPushButton("Open the selected file", self)
        self.scroll_area_layout.addWidget(self.open_button)
        self.open_button.clicked.connect(self.open_file)

        self.x_variable_label = QLabel("Select X-Axis Variable:", self)
        self.scroll_area_layout.addWidget(self.x_variable_label)

        self.xvariables_group = QGroupBox("Select X-Axis variables", self)
        self.xvariables_layout = QVBoxLayout()
        self.xvariables_group.setLayout(self.xvariables_layout)
        self.scroll_area_layout.addWidget(self.xvariables_group)

        self.select_all_xvars_button = QPushButton("Select All X-Axis Variables", self)
        self.clear_all_xvars_button = QPushButton("Clear All X-Axis Variables", self)
        self.scroll_area_layout.addWidget(self.select_all_xvars_button)
        self.scroll_area_layout.addWidget(self.clear_all_xvars_button)

        self.select_all_xvars_button.clicked.connect(self.select_all_xvars)
        self.clear_all_xvars_button.clicked.connect(self.clear_all_xvars)

        self.y_variable_label = QLabel("Select Y-Axis Variable:", self)
        self.scroll_area_layout.addWidget(self.y_variable_label)

        self.yvariables_group = QGroupBox("Select Y-Axis variables", self)
        self.yvariables_layout = QVBoxLayout()
        self.yvariables_group.setLayout(self.yvariables_layout)
        self.scroll_area_layout.addWidget(self.yvariables_group)

        self.select_all_yvars_button = QPushButton("Select All Y-Axis Variables", self)
        self.clear_all_yvars_button = QPushButton("Clear All Y-Axis Variables", self)
        self.scroll_area_layout.addWidget(self.select_all_yvars_button)
        self.scroll_area_layout.addWidget(self.clear_all_yvars_button)

        self.select_all_yvars_button.clicked.connect(self.select_all_yvars)
        self.clear_all_yvars_button.clicked.connect(self.clear_all_yvars)

        self.runs_group = QGroupBox("Select Runs")
        self.runs_layout = QVBoxLayout(self.runs_group)
        self.scroll_area_layout.addWidget(self.runs_group)

        self.select_all_runs_button = QPushButton("Select All Runs", self)
        self.clear_all_runs_button = QPushButton("Clear All Runs", self)
        self.scroll_area_layout.addWidget(self.select_all_runs_button)
        self.scroll_area_layout.addWidget(self.clear_all_runs_button)

        self.select_all_runs_button.clicked.connect(self.select_all_runs)
        self.clear_all_runs_button.clicked.connect(self.clear_all_runs)

        self.plot_button = QPushButton("Create and display a graph", self)
        self.scroll_area_layout.addWidget(self.plot_button)
        self.plot_button.clicked.connect(self.plot_scatter_graph)

        self.options_button = QPushButton("Options", self)
        self.scroll_area_layout.addWidget(self.options_button)
        self.options_button.clicked.connect(self.show_options_dialog)

        self.default_directory = "C:/DSSAT48"
        self.current_directory = self.default_directory
        self.file_extension = ".OUT"
        self.data = []

        self.plot_type = "scatter plot"
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

    def select_directory(self):
        self.current_directory = select_directory(self, self.current_directory, self.load_files)

    def load_files(self, directory):
        load_files(self, directory, self.file_extension, self.list_files)

    def list_files(self, directory, extension):
        list_files(self, directory, extension)

    def preview_file(self):
        preview_file(self)

    def open_file(self):
        open_file(self)
        self.display_data()

    def display_data(self):
        self.clear_layout(self.xvariables_layout)  
        self.clear_layout(self.yvariables_layout)
        self.clear_layout(self.runs_layout)         

        runs = set()
        variables = set()

        for entry in self.data:
            runs.add(entry.get('run', 'Unknown'))
            for variable in entry.get('values', []):
                cde = variable.get('cde', 'Unknown')
                variables.add(cde)

        for run in runs:
            checkbox = QCheckBox(run)
            self.runs_layout.addWidget(checkbox)

        for var in variables:
            checkbox = QCheckBox(var)
            self.xvariables_layout.addWidget(checkbox)  


        for var in variables:
            checkbox = QCheckBox(var)
            self.yvariables_layout.addWidget(checkbox) 
        
            
    def select_all_xvars(self):
        for checkbox in self.xvariables_group.findChildren(QCheckBox):
            checkbox.setChecked(True)

    def clear_all_xvars(self):
        for checkbox in self.xvariables_group.findChildren(QCheckBox):
            checkbox.setChecked(False)

    def select_all_yvars(self):
        for checkbox in self.yvariables_group.findChildren(QCheckBox):
            checkbox.setChecked(True)

    def clear_all_yvars(self):
        for checkbox in self.yvariables_group.findChildren(QCheckBox):
            checkbox.setChecked(False)

    def select_all_runs(self):
        for checkbox in self.runs_group.findChildren(QCheckBox):
            checkbox.setChecked(True)

    def clear_all_runs(self):
        for checkbox in self.runs_group.findChildren(QCheckBox):
            checkbox.setChecked(False)

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def plot_scatter_graph(self):
        selected_x_vars = [checkbox.text() for checkbox in self.xvariables_group.findChildren(QCheckBox) if checkbox.isChecked()]
        selected_y_vars = [checkbox.text() for checkbox in self.yvariables_group.findChildren(QCheckBox) if checkbox.isChecked()]
        selected_runs = [checkbox.text() for checkbox in self.runs_group.findChildren(QCheckBox) if checkbox.isChecked()]

        if not selected_x_vars or not selected_y_vars:
            QMessageBox.warning(self, "Warning!", "Select at least one variable for both X and Y axes.")
            return

        if not selected_runs:
            QMessageBox.warning(self, "Warning!", "Select at least one run to generate the graph.")
            return

        plot_data = []

        for entry in self.data:
            run_name = entry.get('run', 'Unknown')
            if run_name not in selected_runs:
                continue

            for x_var in selected_x_vars:
                for y_var in selected_y_vars:
                    x_values, y_values = None, None

                    for variable in entry.get('values', []):
                        cde = variable.get('cde', 'Unknown')
                        if cde == x_var:
                            x_values = variable.get('values', [])
                        elif cde == y_var:
                            y_values = variable.get('values', [])

                    if x_values is not None and y_values is not None:
                        try:
                            x_values = list(map(float, x_values))
                            y_values = list(map(float, y_values))

                            if len(x_values) == len(y_values):
                                plot_data.append((x_values, y_values, f"{run_name}: {x_var} vs {y_var}"))
                            else:
                                QMessageBox.warning(self, "Warning!", f"Mismatch in the length of data for {run_name}")
                        except ValueError as e:
                            QMessageBox.warning(self, "Warning!", f"Error converting values to float: {e}")

        if not plot_data:
            QMessageBox.warning(self, "Warning!", "No valid data to generate the scatter plot.")
            return

        self.graph_window = GraphWindow(plot_data, "scatter", self.data, self.xvariables_group, self.runs_group)
        graph_scatter(self.graph_window.figure, plot_data)  
        self.graph_window.show()
        

if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainWindow = ScatterPlotWindow()
    sys.exit(app.exec_())