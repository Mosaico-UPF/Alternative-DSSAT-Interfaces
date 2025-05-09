import sys
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import (QApplication, QMainWindow, QMessageBox, QVBoxLayout, QLabel, QListWidget, QPushButton, 
                             QWidget, QCheckBox, QGroupBox, QScrollArea, QSizePolicy, 
                             QDialog, QRadioButton, QButtonGroup, QFormLayout, QAbstractItemView, 
                             QTabWidget, QHBoxLayout)
from common_functions import print_graph, export_data_to_txt_time_series, export_data_to_excel_times_series, select_directory, load_files, list_files, preview_file, open_file, close_time_series, get_file_type
import warnings
from datetime import datetime, timedelta
warnings.filterwarnings("ignore", category=DeprecationWarning)

qt_plugin_path = os.path.join(os.path.dirname(sys.executable), 'Lib', 'site-packages', 'PyQt5', 'Qt', 'plugins', 'platforms')
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = qt_plugin_path

class GraphWindow(QWidget):
    def __init__(self, plot_data, plot_type, data, variables_group, runs_group, force_calendar_mode=False):
        super().__init__()
        self.data = data
        self.plot_data = plot_data
        self.variables_group = variables_group
        self.runs_group = runs_group
        self.force_calendar_mode = force_calendar_mode 

        self.setWindowTitle("Graph Window")
        self.setGeometry(100, 100, 1000, 700)

        self.figure = plt.Figure(figsize=(9, 6), tight_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        control_panel = QWidget()
        control_layout = QVBoxLayout()

        self.toggle_legend_btn = QPushButton("Hide Legend")
        self.toggle_legend_btn.setCheckable(True)
        self.toggle_legend_btn.clicked.connect(self.toggle_legend)

        self.date_mode_label = QLabel("Date Mode:")
        self.date_mode_calendar = QRadioButton("Calendar Days")
        self.date_mode_dap = QRadioButton("Days After Planting")
        self.date_mode_calendar.setChecked(True)

        self.date_mode_group = QButtonGroup()
        self.date_mode_group.addButton(self.date_mode_calendar)
        self.date_mode_group.addButton(self.date_mode_dap)

        if self.force_calendar_mode:
            self.date_mode_dap.setEnabled(False)
            self.date_mode_dap.setChecked(False)
            self.date_mode_dap.setStyleSheet("color: gray;")
            self.date_mode_calendar.setChecked(True)


        self.print_btn = QPushButton("Print")
        self.export_txt_btn = QPushButton("Export TXT")
        self.export_excel_btn = QPushButton("Export Excel")


        control_layout.addWidget(self.toggle_legend_btn)
        control_layout.addWidget(self.date_mode_label)
        control_layout.addWidget(self.date_mode_calendar)
        control_layout.addWidget(self.date_mode_dap)
        control_layout.addStretch(1)
        control_layout.addWidget(self.print_btn)
        control_layout.addWidget(self.export_txt_btn)
        control_layout.addWidget(self.export_excel_btn)
        control_panel.setLayout(control_layout)
        control_panel.setFixedWidth(180)

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.canvas)
        main_layout.addWidget(control_panel)
        self.setLayout(main_layout)

        self.legend_visible = True
        self.refresh_plot(plot_type)

        self.print_btn.clicked.connect(lambda: print_graph(self.canvas, self))
        self.export_txt_btn.clicked.connect(lambda: export_data_to_txt_time_series(self.plot_data, self))
        self.export_excel_btn.clicked.connect(lambda: export_data_to_excel_times_series(self.plot_data, self))

    def toggle_legend(self):
        self.legend_visible = not self.legend_visible
        self.refresh_plot()
        self.toggle_legend_btn.setText("Show Legend" if not self.legend_visible else "Hide Legend")

    def refresh_plot(self, plot_type=None):
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        if plot_type is None:
            plot_type = "scatter" if any(len(d['x']) == 1 for d in self.plot_data) else "time series"

        if self.force_calendar_mode:
            use_calendar_mode = True
        else:
            use_calendar_mode = self.date_mode_calendar.isChecked()

        for data in self.plot_data:
            if plot_type == "time series":
                ax.plot(data['x'], data['y'], label=data['label'])
            else:
                ax.scatter(data['x'], data['y'], label=data['label'])

        ax.set_xlabel('Calendar Day' if use_calendar_mode else 'Days After Planting')
        ax.set_ylabel('Value')
        ax.grid(True)

        if use_calendar_mode:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            self.figure.autofmt_xdate()


        if self.legend_visible:
            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        else:
            ax.legend().remove()

        self.canvas.draw()
        
class OptionsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Options")
        self.setGeometry(200, 200, 300, 200)
        self.plot_type = "time series"

        layout = QFormLayout()
        self.evaluate_file_radio = QRadioButton("Evaluate File")
        self.scatter_plot_radio = QRadioButton("Scatter Plot")
        self.scatter_plot_radio.setChecked(False)
        self.evaluate_file_radio.setChecked(True)

        self.plot_type_group = QButtonGroup()
        self.plot_type_group.addButton(self.evaluate_file_radio)
        self.plot_type_group.addButton(self.scatter_plot_radio)

        layout.addRow("Plot Type:", self.evaluate_file_radio)
        layout.addRow("", self.scatter_plot_radio)
        self.apply_button = QPushButton("Apply", self)
        self.apply_button.clicked.connect(self.apply)
        layout.addWidget(self.apply_button)

        self.setLayout(layout)

    def apply(self):
        plot_type = self.get_plot_type()
        close_time_series(self.parent()) 

        if plot_type == "scatter plot":
            from scatter_plot import ScatterPlotWindow
            self.open_new_window(ScatterPlotWindow)
        elif plot_type == "evaluate file":
            from evaluate import EvaluateWindow
            self.open_new_window(EvaluateWindow)

        self.close()  

    def get_plot_type(self):
        return "scatter plot" if self.scatter_plot_radio.isChecked() else "evaluate file"

    def open_new_window(self, window_class):
        self.parent().open_window(window_class)

class TimeSeriesWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DSSAT Output Viewer - Time Series")
        self.setGeometry(100, 100, 1200, 800)

        self.current_window = None

        self.centralwidget = QWidget(self)
        self.setCentralWidget(self.centralwidget)
        self.main_layout = QVBoxLayout(self.centralwidget)

        self.tabs = QTabWidget(self)
        self.main_layout.addWidget(self.tabs)

        self.files_tab = QWidget()
        self.graphs_tab = QWidget()

        self.tabs.addTab(self.files_tab, "Files")
        self.tabs.addTab(self.graphs_tab, "Graphs")

        self.files_layout = QVBoxLayout(self.files_tab)
        self.graphs_layout = QVBoxLayout(self.graphs_tab)

        self.label = QLabel("Select an Output or Experimental file:", self)
        self.files_layout.addWidget(self.label)

        self.listWidget = QListWidget(self)
        self.files_layout.addWidget(self.listWidget)
        self.listWidget.setSelectionMode(QAbstractItemView.MultiSelection)

        self.select_button = QPushButton("Select a directory", self)
        self.files_layout.addWidget(self.select_button)
        self.select_button.clicked.connect(self.select_directory)

        self.preview_button = QPushButton("Preview the selected file", self)
        self.files_layout.addWidget(self.preview_button)
        self.preview_button.clicked.connect(self.preview_file)

        self.open_button = QPushButton("Open the selected file", self)
        self.files_layout.addWidget(self.open_button)
        self.open_button.clicked.connect(self.open_file)

        self.variables_group = QGroupBox("Select variables")
        self.variables_layout = QVBoxLayout()
        self.variables_group.setLayout(self.variables_layout)
        self.files_layout.addWidget(self.variables_group)

        self.clear_all_vars_button = QPushButton("Clear All Variables", self)
        self.clear_all_vars_button.clicked.connect(self.clear_all_vars)
        self.files_layout.addWidget(self.clear_all_vars_button)

        self.runs_group = QGroupBox("Select Runs")
        self.runs_layout = QVBoxLayout()
        self.runs_group.setLayout(self.runs_layout)
        self.files_layout.addWidget(self.runs_group)

        self.clear_all_runs_button = QPushButton("Clear All Runs", self)
        self.clear_all_runs_button.clicked.connect(self.clear_all_runs)
        self.files_layout.addWidget(self.clear_all_runs_button)

        self.plot_button = QPushButton("Create and display a graph", self)
        self.files_layout.addWidget(self.plot_button)
        self.plot_button.clicked.connect(self.plot_time_series_graph)

        self.options_button = QPushButton("Options", self)
        self.files_layout.addWidget(self.options_button)
        self.options_button.clicked.connect(self.show_options_dialog)

        self.default_directory = "C:/DSSAT48"
        self.current_directory = self.default_directory
        self.file_extension = ".OUT"
        self.data = []

        self.plot_type = "time series"  
        self.show()

        self.scroll_area_files = QScrollArea(self.files_tab)
        self.scroll_area_files.setWidgetResizable(True)

        self.scroll_widget_files = QWidget(self)
        self.scroll_area_files.setWidget(self.scroll_widget_files)

        self.scroll_layout_files = QVBoxLayout(self.scroll_widget_files)
        self.scroll_layout_files.addWidget(self.label)
        self.scroll_layout_files.addWidget(self.listWidget)
        self.scroll_layout_files.addWidget(self.select_button)
        self.scroll_layout_files.addWidget(self.preview_button)
        self.scroll_layout_files.addWidget(self.open_button)
        self.scroll_layout_files.addWidget(self.variables_group)
        self.scroll_layout_files.addWidget(self.clear_all_vars_button)
        self.scroll_layout_files.addWidget(self.runs_group)
        self.scroll_layout_files.addWidget(self.clear_all_runs_button)
        self.scroll_layout_files.addWidget(self.plot_button)
        self.scroll_layout_files.addWidget(self.options_button)

        self.files_layout.addWidget(self.scroll_area_files)

    def closeEvent(self, event):
        event.accept() 

    def open_window(self, window_class, *args):
        if self.current_window is not None:
            self.current_window.close()
        self.current_window = window_class(*args) 
        self.current_window.show()

    def show_options_dialog(self):
        dialog = OptionsDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.plot_type = dialog.get_plot_type()
            self.display_data() 

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

    def display_data(self):
        self.clear_layout(self.variables_layout)
        self.clear_layout(self.runs_layout)

        runs = set()
        variables = set()

        print(f"API Response: {self.data}")

        for entry in self.data:
            if not entry or not isinstance(entry, dict):
                continue 
            
            run = entry.get('run', 'Unknown')
            runs.add(run)
            
            values = entry.get('values', [])
            if values:
                for variable in values:
                    cde = variable.get('cde', 'Unknown')
                    variables.add(cde)

        print(f"Runs: {runs}, Variables: {variables}")

        for run in runs:
            checkbox = QCheckBox(str(run))
            self.runs_layout.addWidget(checkbox)

        for var in variables:
            checkbox = QCheckBox(var)
            self.variables_layout.addWidget(checkbox)


    def clear_all_vars(self):
        for checkbox in self.variables_group.findChildren(QCheckBox):
            checkbox.setChecked(False)

    def clear_all_runs(self):
        for checkbox in self.runs_group.findChildren(QCheckBox):
            checkbox.setChecked(False)

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def validate_file_type(self):
        source_files = []
        for entry in self.data:
            source_file = entry.get('source_file', '')
            if source_file:
                source_files.append(source_file)

        print("SOURCE FILES:", source_files)

        file_types = {get_file_type(f).lower() for f in source_files if f}
        print("FILE TYPES:", file_types)

        graph_window = getattr(self, "graph_window", None)
        if not graph_window:
            print("Graph window not found, skipping validate_file_type.")
            return

        if "t" in file_types:
            graph_window.date_mode_dap.setEnabled(False)
            graph_window.date_mode_dap.setChecked(False)  
            graph_window.date_mode_dap.setStyleSheet("color: gray;")
            graph_window.date_mode_calendar.setChecked(True)
            QMessageBox.information(self, "Calendar Mode Enforced", "T-file detected. Calendar day mode is enforced.")
        else:
            graph_window.date_mode_dap.setEnabled(True)
            graph_window.date_mode_dap.setStyleSheet("")

    def plot_time_series_graph(self):
        print("plot_time_series_graph() called")

        selected_runs = [checkbox.text() for checkbox in self.runs_group.findChildren(QCheckBox) if checkbox.isChecked()]
        selected_vars = [checkbox.text() for checkbox in self.variables_group.findChildren(QCheckBox) if checkbox.isChecked()]

        print("Selected Runs:", selected_runs)
        print("Selected Variables:", selected_vars)

        if not selected_runs or not selected_vars:
            QMessageBox.warning(self, "Warning!", "Select at least one run and one variable")
            return

        plot_data = []
        is_tfile = any(entry.get("file_type") == "t" for entry in self.data)

        for entry in self.data:
            run_name = entry.get('run', 'Unknown')
            if run_name not in selected_runs:
                continue

            for variable in entry.get('values', []):
                cde = variable.get('cde', 'Unknown')
                if cde in selected_vars:
                    values = variable.get('values', [])
                    if not values:
                        continue

                    try:
                        y_values = list(map(float, values))

                        if is_tfile:
                            day_str = entry.get('day', '')
                            try:
                                start_date = datetime.strptime(day_str, '%Y-%m-%d')
                                x_values = [start_date + timedelta(days=i) for i in range(len(y_values))]
                            except (ValueError, TypeError) as e:
                                print(f"Invalid or missing 'day' in .t file: {day_str}. Error: {e}")
                                x_values = list(range(len(y_values)))
                        else:
                            use_calendar_mode = True
                            if hasattr(self, 'graph_window') and hasattr(self.graph_window, 'date_mode_calendar'):
                                use_calendar_mode = self.graph_window.date_mode_calendar.isChecked()

                                start_date = entry.get('start_date')
                                try:
                                    if not isinstance(start_date, datetime):
                                        start_date = datetime.strptime(start_date, '%Y-%m-%d')
                                    if use_calendar_mode:
                                        x_values = [start_date + timedelta(days=i) for i in range(len(y_values))]
                                    else:
                                        x_values = list(range(len(y_values)))  # DAP
                                except Exception as e:
                                    print(f"Error parsing start_date '{start_date}': {e}")
                                    x_values = list(range(len(y_values)))

                                else:
                                    print(f"Invalid start_date for {run_name}: {start_date}")
                                    x_values = list(range(len(y_values)))
                            else:
                                x_values = list(range(len(y_values)))

                        plot_data.append({
                            'x': x_values,
                            'y': y_values,
                            'label': f'{cde} ({run_name})'
                        })

                    except ValueError as e:
                        print(f"ValueError for {cde}: {e}")
                        continue

        if not plot_data:
            QMessageBox.warning(self, "Warning!", "No valid data to generate the graph")
            return

        for i in reversed(range(self.graphs_layout.count())):
            widget = self.graphs_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        is_tfile = any(entry.get("file_type") == "t" for entry in self.data)

        self.graph_window = GraphWindow(plot_data, "time series", self.data,
                                        self.variables_group, self.runs_group,
                                        force_calendar_mode=is_tfile)

        self.graphs_layout.addWidget(self.graph_window)

        self.validate_file_type()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TimeSeriesWindow()
    sys.exit(app.exec_())