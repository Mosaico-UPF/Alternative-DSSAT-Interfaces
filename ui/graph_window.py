import sys
import os
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QRadioButton, QButtonGroup, QLabel, QSizePolicy, QDialog, QTableWidget, QTableWidgetItem
from PyQt5.QtCore import Qt
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

try:
    from ..plots.plotting import plot_time_series, plot_scatter, plot_evaluate
    from ..data.data_processor import get_file_type
    from ..export.export_functions import (
        export_data_to_txt_time_series, export_data_to_excel_time_series,
        export_data_to_txt_scatter, export_data_to_excel_scatter,
        export_data_to_txt_evaluate, export_data_to_excel_evaluate
    )
    from ..utils.stats_calculator import calculate_statistics, extract_normalized_series
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from data.data_processor import get_file_type
    from plots.plotting import plot_time_series, plot_scatter, plot_evaluate
    from export.export_functions import (
        export_data_to_txt_time_series, export_data_to_excel_time_series,
        export_data_to_txt_scatter, export_data_to_excel_scatter,
        export_data_to_txt_evaluate, export_data_to_excel_evaluate, export_tfile_to_txt, export_tfile_to_excel
    )
    from utils.stats_calculator import calculate_statistics, extract_normalized_series

def print_graph(canvas, parent):
    """Print the graph canvas using a print dialog.
    
    Args:
        canvas: Matplotlib FigureCanvas to print.
        parent: Parent widget for the print dialog.
    """
    printer = QPrinter(QPrinter.HighResolution)
    dialog = QPrintDialog(printer, parent)
    if dialog.exec_() == QDialog.Accepted:
        canvas.print_(printer)

class GraphWindow(QWidget):
    """Window for displaying graphs with control options for legend, date mode, and exports."""
    def __init__(self, plot_data, plot_type, data, variables_group, runs_group, filename, parent=None, sim_vs_meas=False):
        """Initialize the graph window with plot data and control panel.
        
        Args:
            plot_data (list): Data for plotting (format depends on plot_type).
            plot_type (str): Type of plot ("time series", "scatter plot", or "evaluate data").
            data (list): Raw data for statistics and processing.
            variables_group (list): Selected variables for display.
            runs_group (list): Selected runs for display.
            filename (str): Path to the data file.
            parent: Parent widget for the dialog.
            sim_vs_meas (bool): Flag to indicate Simulated vs Measured mode (default: False).
        """
        super().__init__(parent)
        # Store initialization data 
        self.filename = filename
        self.current_filename = filename
        self.file_type = get_file_type(self.filename)
        self.data = data
        self.plot_data = plot_data
        self.variables_group = variables_group
        self.runs_group = runs_group
        self.plot_type = plot_type.lower()
        self.sim_vs_meas = sim_vs_meas

        # Enable date mode for time series with .out files.
        self.enable_date_mode = (
            self.plot_type == "time series"
            and any(str(entry.get("file_type", "")).lower() in ("out", "t", "merged")
                    for entry in data if isinstance(entry, dict))
        )

        # Set window properties
        self.setWindowTitle(f"{plot_type.title()} Graph Window")
        self.setGeometry(100, 100, 1000, 700)

        # Create matplotlib figure and canvas
        self.figure = plt.Figure(figsize=(9, 6), tight_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Interactive toolbar
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.setStyleSheet("QToolBar { border: 0px; }")

        # Create control panel
        control_panel = QWidget()
        control_layout = QVBoxLayout()

        # Legend toggle button 
        self.toggle_legend_btn = QPushButton("Hide Legend")
        self.toggle_legend_btn.setCheckable(True)
        self.toggle_legend_btn.clicked.connect(self.toggle_legend)

        # Date mode controls
        self.date_mode_label = QLabel("Date Mode:")
        self.date_mode_calendar = QRadioButton("Calendar Days")
        self.date_mode_dap = QRadioButton("Days After Planting")
        self.date_mode_calendar.setChecked(True)

        self.date_mode_group = QButtonGroup()
        self.date_mode_group.addButton(self.date_mode_calendar)
        self.date_mode_group.addButton(self.date_mode_dap)

        self.date_mode_calendar.toggled.connect(self.refresh_plot)
        self.date_mode_dap.toggled.connect(self.refresh_plot)

        # Disable date mode controls if not applicable
        if not self.enable_date_mode:
            self.date_mode_calendar.setEnabled(False)
            self.date_mode_calendar.setStyleSheet("color: gray;")
            self.date_mode_dap.setEnabled(False)
            self.date_mode_dap.setStyleSheet("color: gray;")

        # Create action buttons
        self.print_btn = QPushButton("Print")
        self.export_txt_btn = QPushButton("Export data to text file")
        self.export_excel_btn = QPushButton("Export to Excel")
        self.statistic_btn = QPushButton("Statistic")
        self.statistic_btn.clicked.connect(self.show_statistics)
        # Enable statistic button for evaluate files, sim-vs-obs supported OUT files, or sim_vs_meas mode
        sim_vs_obs_files = ["plantgro.out", "plantn.out", "soilwat.out"]
        self.statistic_btn.setEnabled(self.sim_vs_meas or (self.filename and os.path.basename(self.filename).lower() in sim_vs_obs_files))

        # Add widgets to control panel layout
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

        # Main layout: toolbar + canvas on the left, controls on the right
        plot_layout = QVBoxLayout()
        plot_layout.addWidget(self.toolbar)   
        plot_layout.addWidget(self.canvas)   
        
         
         

        main_layout = QHBoxLayout()
        main_layout.addLayout(plot_layout, stretch=1)
        main_layout.addWidget(control_panel)
        self.setLayout(main_layout)

        # Initialize legend state and plot
        self.legend_visible = True
        self.refresh_plot()

        # Connect button actions
        self.print_btn.clicked.connect(lambda: print_graph(self.canvas, self))
        if self.plot_type == "time series":
            if self.file_type == "t":
                self.export_txt_btn.clicked.connect(lambda: export_tfile_to_txt(self.plot_data, self, self.date_mode_calendar.isChecked()))
                self.export_excel_btn.clicked.connect(lambda: export_tfile_to_excel(self.plot_data, self, self.date_mode_calendar.isChecked()))
            else:
                self.export_txt_btn.clicked.connect(lambda: export_data_to_txt_time_series(self.plot_data, self))
                self.export_excel_btn.clicked.connect(lambda: export_data_to_excel_time_series(self.plot_data, self))
        elif self.plot_type in ["scatter_plot", "scatter_sim_vs_meas"]:
            self.export_txt_btn.clicked.connect(lambda: export_data_to_txt_scatter(self))
            self.export_excel_btn.clicked.connect(lambda: export_data_to_excel_scatter(self))
        elif self.plot_type == "evaluate data":
            self.export_txt_btn.clicked.connect(lambda: export_data_to_txt_evaluate(self))
            self.export_excel_btn.clicked.connect(lambda: export_data_to_excel_evaluate(self))

    def toggle_legend(self):
        """Toggle the visibility of the plot legend."""
        self.legend_visible = not self.legend_visible
        self.refresh_plot()
        self.toggle_legend_btn.setText("Show Legend" if not self.legend_visible else "Hide Legend")

    def refresh_plot(self):
            """Refresh the plot based on the current plot type and settings."""
            if self.plot_type == "time series":
                use_calendar_mode = self.date_mode_calendar.isChecked() if self.enable_date_mode else True
                plot_time_series(self.figure, self.plot_data, use_calendar_mode, self.legend_visible)
            elif self.plot_type in ["scatter_plot", "scatter_sim_vs_meas"]:
                plot_scatter(self.figure, self.plot_data, self.legend_visible, self.sim_vs_meas)
            elif self.plot_type == "evaluate data":
                plot_evaluate(self.figure, self.plot_data, self.legend_visible)
            else:
                print(f"Unsupported plot type: {self.plot_type}")
            self.canvas.draw()  # Ensure the canvas updates the display

    def show_statistics(self):
        """Display a table of statistics for the selected variables when the Statistic button is clicked."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Statistical Analysis")
        dialog.setGeometry(150, 150, 800, 400)

        table = QTableWidget()
        table.setRowCount(len(self.plot_data))
        table.setColumnCount(13)  # Updated for Variable and Run
        table.setHorizontalHeaderLabels([
            "Variable", "Run", "Mean (Obs)", "Mean (Sim)", "Mean Ratio", "Std.Dev (Obs)",
            "Std.Dev (Sim)", "r-Square", "Mean Diff.", "Mean Abs. Diff.", "RMSE", "d-stat", "Used Obs.", "Total Obs."
        ])

        for row, data in enumerate(self.plot_data):
            variable = data.get('variable', data['label'].split(" (")[0])
            run = data.get('run', 'Unknown')
            observed, simulated = extract_normalized_series(self.data, variable, run)
            stats = calculate_statistics(observed, simulated)
            if stats:
                table.setItem(row, 0, QTableWidgetItem(variable))
                table.setItem(row, 1, QTableWidgetItem(run))
                for col, (key, value) in enumerate(stats.items(), 2):
                    item = QTableWidgetItem(str(value) if value is not None else "N/A")
                    table.setItem(row, col, item)

        layout = QVBoxLayout()
        layout.addWidget(table)
        dialog.setLayout(layout)
        dialog.exec_()

def open_graph_window(plot_data, plot_type, data, variables_group, runs_group, filename, parent=None, sim_vs_meas=False):
    """Open a new graph window with the specified plot data and settings.
    
    Args:
        plot_data (list): Data for plotting (format depends on plot_type).
        plot_type (str): Type of plot ("time series", "scatter plot", or "evaluate data").
        data (list): Raw data for statistics and processing.
        variables_group (list): Selected variables for display.
        runs_group (list): Selected runs for display.
        filename (str): Path to the data file.
        parent: Parent widget for the window.
        sim_vs_meas (bool): Flag to indicate Simulated vs Measured mode (default: False).

    Returns:
        GraphWindow: The created graph window instance.
    """
    window = GraphWindow(plot_data, plot_type, data, variables_group, runs_group, filename, parent, sim_vs_meas)
    window.show()
    return window