# C:\Users\User\Documents\Projetos\interface_Gbuild_refatorada\ui\main_window.py
import os
from PyQt5.QtWidgets import (
    QAction, QApplication, QMainWindow, QLabel, QMessageBox, QWidget, QVBoxLayout, QHBoxLayout
)
from PyQt5.QtGui import QPixmap, QFont
import sys
from PyQt5.QtCore import Qt, QSize
from .file_selector import open_file_selector
from .time_series_var_selection import open_time_series_var_selection
from .graph_window import open_graph_window  # Import for graph display

try:
    from .time_series_var_selection import open_time_series_var_selection
    from .scatter_plot_var_selection import open_scatter_var_selection
    from .evaluate_var_selection import open_evaluate_var_selection
    from .options_menu import OptionsDialog
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from ui.time_series_var_selection import open_time_series_var_selection
    from ui.scatter_plot_var_selection import open_scatter_var_selection
    from ui.evaluate_var_selection import open_evaluate_var_selection
    from ui.options_menu import OptionsDialog

class MainWindow(QMainWindow):
    """Main application window for the DSSAT Output Viewer."""
    def __init__(self):
        """Initialize the main window logo, title, and menu bar."""
        super().__init__()
        # Set window properties
        self.setWindowTitle("DSSAT Output Viewer - Main Window")
        self.resize(900, 600)

        # Set up central widget and main layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setAlignment(Qt.AlignCenter)

        # Central logo and title
        logo_and_title_widget = QWidget()
        logo_and_title_layout = QHBoxLayout(logo_and_title_widget)
        logo_and_title_layout.setAlignment(Qt.AlignCenter)

        # DSSAT logo
        logo_label = QLabel()
        pixmap = QPixmap(os.path.join(os.path.dirname(__file__), "Logo.png"))  # path to logo
        scaled_pixmap = pixmap.scaledToHeight(140, Qt.SmoothTransformation)
        logo_label.setPixmap(scaled_pixmap)
        logo_label.setAlignment(Qt.AlignCenter)
        logo_and_title_layout.addWidget(logo_label)

        # GBuild text
        text_label = QLabel("GBuild")
        font = QFont("Arial", 40)
        text_label.setFont(font)
        text_label.setAlignment(Qt.AlignCenter)
        logo_and_title_layout.addWidget(text_label)

        # Add logo+title to the main layout
        self.main_layout.addWidget(logo_and_title_widget)

        # Placeholder for graph selection UI
        self.graph_selection_widget = QWidget()
        self.graph_selection_layout = QVBoxLayout(self.graph_selection_widget)
        self.main_layout.addWidget(self.graph_selection_widget)

        # Store selected files and current graph type
        self.selected_files = []
        self.current_graph_type = "Time Series"
        self.show_var_selection = False
        self.last_dir = None
        self.sim_vs_meas_mode = False  # Flag for Simulated vs Measured mode

        # Menu bar
        menubar = self.menuBar()

        # Menu File
        file_menu = menubar.addMenu("File")
        open_action = file_menu.addAction("Open...")
        open_action.triggered.connect(self.open_file)
        file_menu.addSeparator()
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)

        # Menu Variable Selection
        var_action = QAction("Variable Selection", self)
        var_action.triggered.connect(self.show_variable_selection)
        menubar.addAction(var_action)

        # Options Menu
        options_action = QAction("Options", self)
        options_action.triggered.connect(self.show_options)
        menubar.addAction(options_action)

        # Menu Help
        help_menu = menubar.addMenu("Help")
        contents_action = help_menu.addAction("Contents")
        contents_action.triggered.connect(lambda: QMessageBox.information(self, "Help", "Contents not implemented yet"))
        support_action = help_menu.addAction("Technical support")
        support_action.triggered.connect(lambda: QMessageBox.information(self, "Help", "Technical support info here"))
        about_action = help_menu.addAction("About")
        about_action.triggered.connect(lambda: QMessageBox.information(self, "About", "Alternative GBuild UI v1.0\nBy Fred (for now, at least)"))

    def open_file(self):
            """Open the file selector and load the time series selection by default."""
            selected_files, current_dir = open_file_selector(self, initial_dir=self.last_dir)
            if selected_files:
                self.selected_files = selected_files
                self.last_dir = current_dir
                self.current_graph_type = "Time Series"  # Default
                self.switch_graph_type()
            else:
                self.last_dir = current_dir
                self.clear_graph_selection()

    def switch_graph_type(self):
            """Switch between different graph types without opening the dialog unless requested."""
            self.clear_graph_selection()

            if self.show_var_selection:
                if self.current_graph_type == "Time Series":
                    runs, vars, data = open_time_series_var_selection(self.selected_files, self)
                    if runs and vars and data:
                        graph_window = open_graph_window(data, self.current_graph_type, data, vars, runs, self.selected_files[0], self)
                        self.graph_selection_layout.addWidget(graph_window)
                    elif runs is not None or vars is not None or data is not None:
                        pass  # Suppress warning if dialog was just closed
                elif self.current_graph_type == "Scatter Plot":
                    runs, (x_vars, y_vars), data = open_scatter_var_selection(self.selected_files, self, sim_vs_meas=False)
                    if runs and x_vars and y_vars and data:
                        graph_window = open_graph_window(data, self.current_graph_type, data, x_vars + y_vars, runs, self.selected_files[0], self)
                        self.graph_selection_layout.addWidget(graph_window)
                    elif runs is not None or x_vars is not None or y_vars is not None or data is not None:
                        pass  # Suppress warning if dialog was just closed
                elif self.current_graph_type == "Scatter Plot (Sim vs Meas)":
                    runs, vars, data = open_scatter_var_selection(self.selected_files, self, sim_vs_meas=True)
                    if runs and vars and data:
                        graph_window = open_graph_window(data, self.current_graph_type, data, vars, runs, self.selected_files[0], self, sim_vs_meas=True)
                        self.graph_selection_layout.addWidget(graph_window)
                    elif runs is not None or vars is not None or data is not None:
                        pass  # Suppress warning if dialog was just closed
                elif self.current_graph_type == "Evaluate":
                    vars, data = open_evaluate_var_selection(self.selected_files, self)
                    if vars and data:
                        graph_window = open_graph_window(data, self.current_graph_type, data, vars, [], self.selected_files[0], self)
                        self.graph_selection_layout.addWidget(graph_window)
                    elif vars is not None or data is not None:
                        pass  # Suppress warning if dialog was just closed
                else:
                    QMessageBox.warning(self, "Warning", f"Unsupported graph type: {self.current_graph_type}")
                self.show_var_selection = False
            else:
                if not self.selected_files:
                    QMessageBox.information(self, "Info", "Please select files first via File > Open.")

    def clear_graph_selection(self):
        """Clear all widgets from the graph selection layout."""
        for i in reversed(range(self.graph_selection_layout.count())):
            widget = self.graph_selection_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

    def show_variable_selection(self):
        """Open the variable selection dialog for the current graph type."""
        if not self.selected_files:
            QMessageBox.warning(self, "Warning", "Please select files first.")
            return
        self.show_var_selection = True
        self.switch_graph_type()

    def show_options(self):
        """Open the options dialog to select plot type."""
        dialog = OptionsDialog(self)
        if dialog.exec_():
            selected_type = dialog.get_plot_type()
            plot_type_map = {
                "time_series": "Time Series",
                "scatter_plot": "Scatter Plot",
                "evaluate": "Evaluate",
                "scatter_sim_vs_meas": "Scatter Plot (Sim vs Meas)"
            }
            if selected_type in plot_type_map:
                self.current_graph_type = plot_type_map[selected_type]
                self.sim_vs_meas_mode = selected_type == "scatter_sim_vs_meas"
                self.switch_graph_type()
            else:
                QMessageBox.warning(self, "Warning", f"Plot type {selected_type} not implemented yet.")

if __name__ == "__main__":
    """Run the main window as a standalone application for testing."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())