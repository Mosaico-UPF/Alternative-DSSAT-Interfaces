import os
import sys
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QScrollArea, QCheckBox,
    QPushButton, QMessageBox, QWidget, QTextEdit, QListWidget, QSizePolicy, QTabWidget,
    QApplication, QLabel
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

try:
    from utils.cde_data_parser import parse_data_cde
    from plots.plotting import plot_time_series, build_plot_data  # Add build_plot_data
    from ui.graph_window import GraphWindow
    from data.data_processor import load_all_file_data, extract_runs_and_variables, get_file_type
except ImportError:
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    sys.path.insert(0, project_root)
    from utils.cde_data_parser import parse_data_cde
    from plots.plotting import plot_time_series, build_plot_data  # Add build_plot_data
    from ui.graph_window import GraphWindow
    from data.data_processor import load_all_file_data, extract_runs_and_variables, get_file_type

class TimeSeriesVarSelectionDialog(QDialog):
    """Dialog for selecting variables and runs for time series visualization."""
    def __init__(self, selected_files, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Time Series Variable and Run Selection")
        self.setGeometry(200, 200, 1000, 700)

        self.selected_files = selected_files
        self.data = []
        self.plot_data = []
        self.graph_window = None

        # Validate file selection
        t_file_count = sum(1 for f in selected_files if get_file_type(os.path.basename(f)) == "t")
        if t_file_count > 1:
            QMessageBox.warning(self, "Warning!", "Only one .t file is allowed to be selected.")
            self.reject()
            return
        out_file_count = sum(1 for f in selected_files if get_file_type(os.path.basename(f)) == "out")
        if t_file_count == 0 and out_file_count == 0:
            QMessageBox.warning(self, "Warning!", "Please select at least one .out or .t file.")
            self.reject()
            return

        # Main layout with tab widget
        self.main_layout = QVBoxLayout()
        self.tab_widget = QTabWidget()
        self.main_layout.addWidget(self.tab_widget)

        # Selection tab
        self.selection_tab = QWidget()
        self.selection_layout = QVBoxLayout(self.selection_tab)

        # Top layout for file display and preview
        self.top_layout = QHBoxLayout()
        self.files_display = QListWidget()
        self.files_display.setMaximumWidth(200)
        num_files = len(selected_files)
        self.files_display.setMaximumHeight(min(20 * num_files, 100))
        self.files_display.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        for file in selected_files:
            self.files_display.addItem(os.path.basename(file))
        self.top_layout.addWidget(self.files_display)

        self.preview_button = QPushButton("Preview File")
        self.preview_button.clicked.connect(self.preview_file)
        self.preview_button.setMaximumWidth(150)
        self.top_layout.addWidget(self.preview_button)
        self.top_layout.addStretch()
        self.selection_layout.addLayout(self.top_layout)

        # Content layout for variable and run selection
        self.content_layout = QHBoxLayout()
        self.variables_group = QGroupBox("Select Variables")
        self.variables_layout = QVBoxLayout()
        self.variables_scroll = QScrollArea()
        self.variables_scroll.setWidgetResizable(True)
        self.variables_widget = QWidget()
        self.variables_widget.setLayout(self.variables_layout)
        self.variables_scroll.setWidget(self.variables_widget)
        self.variables_group.setLayout(QVBoxLayout())
        self.variables_group.layout().addWidget(self.variables_scroll)
        self.content_layout.addWidget(self.variables_group)

        # Runs selection
        self.runs_layout = QVBoxLayout()
        self.runs_layout.setAlignment(Qt.AlignTop)
        self.runs_widget = QWidget()
        self.runs_widget.setLayout(self.runs_layout)
        self.runs_scroll = QScrollArea()
        self.runs_scroll.setWidgetResizable(True)
        self.runs_scroll.setWidget(self.runs_widget)
        self.runs_group = QGroupBox("Select Runs")
        group_layout = QVBoxLayout()
        group_layout.addWidget(self.runs_scroll)
        self.select_all_runs = QCheckBox("Select All Runs")
        self.select_all_runs.stateChanged.connect(self.toggle_all_runs)
        group_layout.addWidget(self.select_all_runs)
        self.runs_group.setLayout(group_layout)
        self.content_layout.addWidget(self.runs_group)

        self.selection_layout.addLayout(self.content_layout)

        # Buttons
        self.button_layout = QHBoxLayout()
        self.clear_button = QPushButton("Clear All")
        self.clear_button.clicked.connect(self.clear_all)
        self.reload_button = QPushButton("Reload Data")
        self.reload_button.clicked.connect(self.reload_data)
        self.graph_button = QPushButton("Create and Display Graph")
        self.graph_button.clicked.connect(self.show_graph_tab)
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.reject)
        self.button_layout.addWidget(self.clear_button)
        self.button_layout.addWidget(self.reload_button)
        self.button_layout.addWidget(self.graph_button)
        self.button_layout.addWidget(self.close_button)
        self.selection_layout.addLayout(self.button_layout)
        self.selection_tab.setLayout(self.selection_layout)

        # Graph tab
        self.graph_tab = QWidget()
        self.graph_layout = QVBoxLayout(self.graph_tab)
        self.back_button = QPushButton("Back to Selection")
        self.back_button.clicked.connect(self.show_selection_tab)
        self.graph_layout.addWidget(self.back_button)
        self.tab_widget.addTab(self.selection_tab, "Selection")
        self.tab_widget.addTab(self.graph_tab, "Graph")
        self.setLayout(self.main_layout)

        # Load data and populate UI
        self.reload_data()

    def reload_data(self):
        """Reload data from files and update UI."""
        self.data, error = load_all_file_data(self.selected_files)
        if error:
            QMessageBox.critical(self, "Error", error)
            self.reject()
            return
        if not self.data:
            QMessageBox.warning(self, "Warning", "No valid data loaded from selected files.")
            self.reject()
            return
        print(f"Loaded data: {len(self.data)} entries")
        self.populate_variables()
        self.populate_runs()

    def clear_layout(self, layout):
        """Remove all widgets from a QLayout."""
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())

    def populate_variables(self):
        """Populate variable selection checkboxes with deduplicated variables."""
        self.clear_layout(self.variables_layout)
        runs, variables = extract_runs_and_variables(self.data)
        cde_descriptions = parse_data_cde()

        # Track CDEs with both simulated and measured data
        cde_types = {}
        for entry in self.data:
            for var in entry.get("values", []):
                cde = var.get("cde")
                var_type = var.get("type", "simulated")
                if cde not in cde_types:
                    cde_types[cde] = set()
                cde_types[cde].add(var_type)

        # Deduplicate variables by CDE, preferring time-series data
        var_info = {}
        for entry in self.data:
            for var in entry.get("values", []):
                cde = var.get("cde")
                if cde in ["DATE", "YEAR", "DOY", "DAP", "DAS"]:
                    continue
                if cde not in var_info or len(var.get("values", [])) > len(var_info.get(cde, {}).get("values", [])):
                    var_info[cde] = var

        print(f"Found {len(var_info)} unique variables for display")
        for cde in sorted(var_info.keys()):
            description = cde_descriptions.get(cde, cde)
            checkbox = QCheckBox(f"{description} ({cde})")
            checkbox.setChecked(False)
            if cde in cde_types and {"simulated", "measured"}.issubset(cde_types[cde]):
                font = QFont()
                font.setBold(True)
                checkbox.setFont(font)
            self.variables_layout.addWidget(checkbox)
        self.variables_layout.addStretch()

    def populate_runs(self):
        """Populate run selection checkboxes."""
        self.clear_layout(self.runs_layout)
        runs, _ = extract_runs_and_variables(self.data)
        print(f"Found {len(runs)} runs for display")
        for run in sorted(runs):
            checkbox = QCheckBox(run)
            checkbox.setChecked(False)
            self.runs_layout.addWidget(checkbox)
        self.runs_layout.addStretch()

    def clear_all(self):
        """Clear all selections."""
        for checkbox in self.variables_widget.findChildren(QCheckBox):
            checkbox.setChecked(False)
        for checkbox in self.runs_widget.findChildren(QCheckBox):
            checkbox.setChecked(False)
        self.select_all_runs.setChecked(False)

    def toggle_all_runs(self, state):
        """Toggle all run checkboxes."""
        for checkbox in self.runs_widget.findChildren(QCheckBox):
            checkbox.setChecked(state == Qt.Checked)

    def preview_file(self):
        """Preview selected file content."""
        selected_items = self.files_display.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Warning", "Please select a file to preview.")
            return
        file_name = selected_items[0].text()
        file_path = next(f for f in self.selected_files if os.path.basename(f) == file_name)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read(1000)  # Limit to first 1000 chars
            preview_dialog = QDialog(self)
            preview_dialog.setWindowTitle(f"Preview: {file_name}")
            layout = QVBoxLayout()
            text_edit = QTextEdit()
            text_edit.setReadOnly(True)
            text_edit.setText(content)
            layout.addWidget(text_edit)
            close_button = QPushButton("Close")
            close_button.clicked.connect(preview_dialog.accept)
            layout.addWidget(close_button)
            preview_dialog.setLayout(layout)
            preview_dialog.resize(600, 400)
            preview_dialog.exec_()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to preview file: {str(e)}")

    def show_graph_tab(self):
        """Create and display the time series graph."""
        selected_vars = [checkbox.text() for checkbox in self.variables_widget.findChildren(QCheckBox) if checkbox.isChecked()]
        selected_runs = [checkbox.text() for checkbox in self.runs_widget.findChildren(QCheckBox) if checkbox.isChecked()]
        if not selected_vars or not selected_runs:
            QMessageBox.warning(self, "Warning", "Please select at least one variable and one run.")
            return

        self.plot_data = []
        for run in selected_runs:
            for var in selected_vars:
                cde = var.split('(')[-1].strip(')') if '(' in var else var
                plot_data = build_plot_data(self.data, cde, run=run, use_calendar=True)  # Use build_plot_data directly
                self.plot_data.extend(plot_data)

        if not self.plot_data:
            QMessageBox.warning(self, "Warning", "No valid data to plot for the selected runs and variables.")
            return

        filename = self.selected_files[0] if self.selected_files else None
        if filename is None:
            QMessageBox.warning(self, "Warning", "No file selected to display graph.")
            return

        if self.graph_window:
            self.graph_window.plot_data = self.plot_data
            self.graph_window.refresh_plot()
        else:
            self.graph_window = GraphWindow(
                self.plot_data,
                "Time Series",
                self.data,
                [var.split('(')[0].strip() for var in selected_vars],
                selected_runs,
                filename,
                self
            )
            self.graph_layout.addWidget(self.graph_window)
        self.tab_widget.setCurrentIndex(1)

    def show_selection_tab(self):
        """Switch back to the selection tab."""
        self.tab_widget.setCurrentIndex(0)

    def get_selections(self):
        """Return the selected runs and variables."""
        selected_runs = [checkbox.text() for checkbox in self.runs_widget.findChildren(QCheckBox) if checkbox.isChecked()]
        selected_vars = [checkbox.text() for checkbox in self.variables_widget.findChildren(QCheckBox) if checkbox.isChecked()]
        return selected_runs, selected_vars, self.data

def open_time_series_var_selection(selected_files, parent=None):
    """Open the time series variable selection dialog and return the selections."""
    dialog = TimeSeriesVarSelectionDialog(selected_files, parent)
    center_window_on_parent(dialog, parent)
    if dialog.exec_():
        return dialog.get_selections()
    return None, None, None

def center_window_on_parent(window, parent):
    """Center the window relative to its parent or screen."""
    if parent is None:
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        center = screen_geometry.center()
    else:
        center = parent.frameGeometry().center()
    geo = window.frameGeometry()
    geo.moveCenter(center)
    window.move(geo.topLeft())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    selected_files = [r"C:\DSSAT48\somefile.out", r"C:\DSSAT48\anothertfile.t"]
    runs, vars, data = open_time_series_var_selection(selected_files)
    print("Selected Runs:", runs)
    print("Selected Variables:", vars)
    print("Data:", data)
    sys.exit(app.exec_())