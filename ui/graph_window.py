# C:\Users\User\Documents\Projetos\interface_Gbuild_refatorada\ui\graph_window.py
import sys
import os
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QRadioButton, QButtonGroup, QLabel, QSizePolicy, QDialog, QTableWidget, QTableWidgetItem
from PyQt5.QtCore import Qt
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

try:
    from ..plots.plotting import plot_time_series, plot_scatter, plot_evaluate
    from ..data.data_processor import get_file_type
    from ..export.export_functions import (
        export_data_to_txt_time_series, export_data_to_excel_time_series,
        export_data_to_txt_scatter, export_data_to_excel_scatter,
        export_data_to_txt_evaluate, export_data_to_excel_evaluate
    )
    from ..utils.stats_calculator import calculate_statistics, get_variable_data
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from data.data_processor import get_file_type
    from plots.plotting import plot_time_series, plot_scatter, plot_evaluate
    from export.export_functions import (
        export_data_to_txt_time_series, export_data_to_excel_time_series,
        export_data_to_txt_scatter, export_data_to_excel_scatter,
        export_data_to_txt_evaluate, export_data_to_excel_evaluate, export_tfile_to_excel, export_tfile_to_txt
    )
    from utils.stats_calculator import calculate_statistics, get_variable_data

    
def print_graph(canvas, parent):
    printer = QPrinter(QPrinter.HighResolution)
    dialog = QPrintDialog(printer, parent)
    if dialog.exec_() == QDialog.Accepted:
        canvas.print_(printer)

class GraphWindow(QWidget):
    def __init__(self, plot_data, plot_type, data, variables_group, runs_group, filename, parent=None):
        super().__init__(parent) 
        self.filename = filename
        self.current_filename = filename
        self.file_type = get_file_type(self.filename)
        self.data = data
        self.plot_data = plot_data
        self.variables_group = variables_group
        self.runs_group = runs_group
        self.plot_type = plot_type.lower()

        self.enable_date_mode = (self.plot_type == "time series" and any(
            entry.get("file_type") == "out" for entry in data if isinstance(entry, dict)
        ))

        self.setWindowTitle(f"{plot_type.title()} Graph Window")
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

        self.date_mode_calendar.toggled.connect(self.refresh_plot)
        self.date_mode_dap.toggled.connect(self.refresh_plot)

        if not self.enable_date_mode:
            self.date_mode_calendar.setEnabled(False)
            self.date_mode_calendar.setStyleSheet("color: gray;")
            self.date_mode_dap.setEnabled(False)
            self.date_mode_dap.setStyleSheet("color: gray;")

        self.print_btn = QPushButton("Print")
        self.export_txt_btn = QPushButton("Export data to text file")
        self.export_excel_btn = QPushButton("Export to Excel")
        self.statistic_btn = QPushButton("Statistic")
        self.statistic_btn.clicked.connect(self.show_statistics)
        # Enable statistic button only for evaluate files
        self.statistic_btn.setEnabled(self.file_type == "evaluate")

        control_layout.addWidget(self.toggle_legend_btn)
        control_layout.addWidget(self.date_mode_label)
        control_layout.addWidget(self.date_mode_calendar)
        control_layout.addWidget(self.date_mode_dap)
        control_layout.addStretch(1)
        control_layout.addWidget(self.print_btn)
        control_layout.addWidget(self.export_txt_btn)
        control_layout.addWidget(self.export_excel_btn)
        control_layout.addWidget(self.statistic_btn)
        control_panel.setLayout(control_layout)
        control_panel.setFixedWidth(180)

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.canvas)
        main_layout.addWidget(control_panel)
        self.setLayout(main_layout)

        self.legend_visible = True
        self.refresh_plot()

        self.print_btn.clicked.connect(lambda: print_graph(self.canvas, self))
        if self.plot_type == "time series":
            if self.file_type == "t":
                self.export_txt_btn.clicked.connect(lambda: export_tfile_to_txt(self.plot_data, self))
                self.export_excel_btn.clicked.connect(lambda: export_tfile_to_excel(self.plot_data, self))
            else:
                self.export_txt_btn.clicked.connect(lambda: export_data_to_txt_time_series(self.plot_data, self))
                self.export_excel_btn.clicked.connect(lambda: export_data_to_excel_time_series(self.plot_data, self))
        elif self.plot_type == "scatter plot":
            self.export_txt_btn.clicked.connect(lambda: export_data_to_txt_scatter(self.plot_data, self))
            self.export_excel_btn.clicked.connect(lambda: export_data_to_excel_scatter(self.plot_data, self))
        elif self.plot_type == "evaluate data":
            self.export_txt_btn.clicked.connect(lambda: export_data_to_txt_evaluate(self.plot_data, self))
            self.export_excel_btn.clicked.connect(lambda: export_data_to_excel_evaluate(self.plot_data, self))

    def toggle_legend(self):
        self.legend_visible = not self.legend_visible
        self.refresh_plot()
        self.toggle_legend_btn.setText("Show Legend" if not self.legend_visible else "Hide Legend")

    def refresh_plot(self):
        if self.plot_type == "time series":
            use_calendar_mode = self.date_mode_calendar.isChecked() if self.enable_date_mode else True
            plot_time_series(self.figure, self.plot_data, use_calendar_mode, self.legend_visible)
        elif self.plot_type == "scatter plot":
            plot_scatter(self.figure, self.plot_data, self.legend_visible)
        elif self.plot_type == "evaluate data":
            plot_evaluate(self.figure, self.plot_data, self.legend_visible)
        else:
            print(f"Unsupported plot type: {self.plot_type}")

    def show_statistics(self):
        """Display a table of statistics for the selected variables."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Statistical Analysis")
        dialog.setGeometry(150, 150, 800, 400)

        table = QTableWidget()
        table.setRowCount(len(self.plot_data))
        table.setColumnCount(12)
        table.setHorizontalHeaderLabels([
            "Variable Name", "Mean (Obs)", "Mean (Sim)", "Mean Ratio", "Std.Dev (Obs)", 
            "Std.Dev (Sim)", "r-Square", "Mean Diff.", "Mean Abs. Diff.", "RMSE", 
            "d-stat", "Used Obs.", "Total Number"
        ])

        for row, data in enumerate(self.plot_data):
            variable_name = data['label'].split(" (")[0]
            observed, simulated = get_variable_data(self.data, variable_name)
            stats = calculate_statistics(observed, simulated)
            if stats:
                table.setItem(row, 0, QTableWidgetItem(variable_name))
                for col, (key, value) in enumerate(stats.items()):
                    item = QTableWidgetItem(str(value))
                    table.setItem(row, col + 1, item)

        layout = QVBoxLayout()
        layout.addWidget(table)
        dialog.setLayout(layout)
        dialog.exec_()
        
def open_graph_window(plot_data, plot_type, data, variables_group, runs_group, filename, parent=None):
    window = GraphWindow(plot_data, plot_type, data, variables_group, runs_group, filename, parent)
    window.show()
    return window