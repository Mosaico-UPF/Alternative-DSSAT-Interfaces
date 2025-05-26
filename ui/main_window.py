# C:\Users\User\Documents\Projetos\interface_Gbuild_refatorada\ui\main_window.py
import os
from PyQt5.QtWidgets import (
    QAction, QApplication, QMainWindow, QLabel, QMessageBox, QWidget, QVBoxLayout, QComboBox
)
import sys
from PyQt5.QtCore import Qt, QSize
from .file_selector import open_file_selector
from .time_series_var_selection import open_time_series_var_selection
try:
    from .time_series_var_selection import open_time_series_var_selection
    from .scatter_plot_var_selection import open_scatter_var_selection
    from .options_menu import OptionsDialog
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from ui.time_series_var_selection import open_time_series_var_selection
    from ui.scatter_plot_var_selection import open_scatter_var_selection
    from ui.options_menu import OptionsDialog

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DSSAT Output Viewer - Main Window")
        self.resize(900, 600)

        # Central widget setup
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # Initial content
        self.label = QLabel("Welcome to DSSAT Output Viewer", self)
        self.label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.label)

        # Placeholder for graph type selection
        self.graph_type_selector = QComboBox()
        self.graph_type_selector.addItems(["Time Series", "Scatter Plot"])
        self.graph_type_selector.setEnabled(False)  # Disabled until files are selected
        self.graph_type_selector.currentIndexChanged.connect(self.switch_graph_type)
        self.main_layout.addWidget(self.graph_type_selector)

        # Placeholder for graph selection UI
        self.graph_selection_widget = QWidget()
        self.graph_selection_layout = QVBoxLayout(self.graph_selection_widget)
        self.main_layout.addWidget(self.graph_selection_widget)

        # Store selected files and current graph type
        self.selected_files = []
        self.current_graph_type = "Time Series"
        self.show_var_selection = False  # Flag to control dialog opening

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
        var_menu = menubar.addMenu("Variable Selection")
        var_action = QAction("Open Variable Selection", self)
        var_action.triggered.connect(self.show_variable_selection)
        var_menu.addAction(var_action)

        # Menu Options
        options_menu = menubar.addMenu("Options")
        options_action = QAction("Options", self)
        options_action.triggered.connect(self.show_options)
        options_menu.addAction(options_action)

        # Menu Help
        help_menu = menubar.addMenu("Help")

        contents_action = help_menu.addAction("Contents")
        contents_action.triggered.connect(lambda: QMessageBox.information(self, "Help", "Contents not implemented yet"))

        support_action = help_menu.addAction("Technical support")
        support_action.triggered.connect(lambda: QMessageBox.information(self, "Help", "Technical support info here"))

        about_action = help_menu.addAction("About")
        about_action.triggered.connect(lambda: QMessageBox.information(self, "About", "DSSAT Viewer v1.0\nBy You"))

    def open_file(self):
        """Open the file selector and load the time series selection by default."""
        selected_files = open_file_selector(self)
        if selected_files:
            self.selected_files = selected_files
            self.label.setText("Files opened:\n" + "\n".join(selected_files))
            self.graph_type_selector.setEnabled(True)
            self.current_graph_type = "Time Series"  # Default
            self.graph_type_selector.setCurrentText(self.current_graph_type)
            self.switch_graph_type()
        else:
            self.label.setText("No files selected.")
            self.graph_type_selector.setEnabled(False)
            self.clear_graph_selection()

    def switch_graph_type(self):
        """Switch between different graph types without opening the dialog unless requested."""
        self.current_graph_type = self.graph_type_selector.currentText()
        self.clear_graph_selection()

        if self.show_var_selection:
            if self.current_graph_type == "Time Series":
                runs, vars, data = open_time_series_var_selection(self.selected_files, self)
                if runs is not None and vars is not None:
                    self.label.setText(f"Time Series - Graph window opened.\nSelected Runs: {', '.join(runs)}\nSelected Variables: {', '.join(vars)}")
                else:
                    self.label.setText("Time Series selection canceled.")
            elif self.current_graph_type == "Scatter Plot":
                runs, (x_vars, y_vars), data = open_scatter_var_selection(self.selected_files, self)
                if runs and x_vars and y_vars:
                    self.label.setText(f"Scatter Plot - Graph window opened.\nSelected Runs: {', '.join(runs)}\nX Variables: {', '.join(x_vars)}\nY Variables: {', '.join(y_vars)}")
                else:
                    self.label.setText("Scatter Plot selection canceled.")
            else:
                self.label.setText(f"{self.current_graph_type} selection not implemented yet.")
            self.show_var_selection = False  # Reset flag after opening dialog
        else:
            self.label.setText(f"Selected graph type: {self.current_graph_type}. Click 'Variable Selection' to configure.")

    def clear_graph_selection(self):
        """Clear the current graph selection UI."""
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
        """Display the options dialog with a collapsible menu for plot types."""
        dialog = OptionsDialog(self)
        if dialog.exec_():
            selected_type = dialog.get_plot_type()
            if selected_type in ["time_series", "scatter_plot"]:
                self.current_graph_type = selected_type.replace("_", " ").title()
                self.graph_type_selector.setCurrentText(self.current_graph_type)
                self.switch_graph_type()
            else:
                QMessageBox.warning(self, "Warning", f"Plot type {selected_type} not implemented yet.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())