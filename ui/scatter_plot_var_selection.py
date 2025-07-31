import os
import sys
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QScrollArea, QCheckBox,
    QPushButton, QMessageBox, QWidget, QTextEdit, QListWidget, QSizePolicy, QTabWidget,
    QApplication, QLabel
)
from PyQt5.QtCore import Qt

try:
    from ..utils.cde_data_parser import parse_data_cde
    from ..data.data_processor import load_all_file_data, extract_runs_and_variables, get_file_type
    from ..ui.graph_window import GraphWindow
except ImportError:
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    sys.path.insert(0, project_root)
    from utils.cde_data_parser import parse_data_cde
    from data.data_processor import load_all_file_data, extract_runs_and_variables, get_file_type
    from ui.graph_window import GraphWindow

class ScatterVarSelectionDialog(QDialog):
    """Dialog for selecting variables and runs for scatter plot visualization"""
    def __init__(self, selected_files, parent=None):
        """Initialize the dialog with file selection and UI setup.
        
        Args:
            selected_files (list): List of file paths to process.
            parent: Parent widget for the dialog.
        """
        super().__init__(parent)
        # Set dialog properties
        self.setWindowTitle("Scatter Plot Variable Selection Menu")
        self.setGeometry(200, 200, 1000, 700)

        # Store selected files and initialize data containers
        self.selected_files = selected_files
        self.data = []
        self.plot_data = []

        # Validation for file types
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

        # Selection Tab
        self.selection_tab = QWidget()
        self.selection_layout = QVBoxLayout(self.selection_tab)

        # Horizontal layout for selected files display and preview button
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

        # X-Axis variables
        self.x_variables_group = QGroupBox("Select X-Axis Variable(s)")
        self.x_variables_layout = QVBoxLayout()
        self.x_variables_scroll = QScrollArea()
        self.x_variables_scroll.setWidgetResizable(True)
        self.x_variables_widget = QWidget()
        self.x_variables_widget.setLayout(self.x_variables_layout)
        self.x_variables_scroll.setWidget(self.x_variables_widget)
        self.x_variables_group.setLayout(QVBoxLayout())
        self.x_variables_group.layout().addWidget(self.x_variables_scroll)
        self.content_layout.addWidget(self.x_variables_group)

        # Y-Axis variables
        self.y_variables_group = QGroupBox("Select Y-Axis Variable(s)")
        self.y_variables_layout = QVBoxLayout()
        self.y_variables_scroll = QScrollArea()
        self.y_variables_scroll.setWidgetResizable(True)
        self.y_variables_widget = QWidget()
        self.y_variables_widget.setLayout(self.y_variables_layout)
        self.y_variables_scroll.setWidget(self.y_variables_widget)
        self.y_variables_group.setLayout(QVBoxLayout())
        self.y_variables_group.layout().addWidget(self.y_variables_scroll)
        self.content_layout.addWidget(self.y_variables_group)

        # Runs selection
        self.runs_layout = QVBoxLayout()
        self.runs_layout.setAlignment(Qt.AlignTop)
        self.runs_widget = QWidget()
        self.runs_widget.setLayout(self.runs_layout)
        self.runs_scroll = QScrollArea()
        self.runs_scroll.setWidgetResizable(True)
        self.runs_scroll.setWidget(self.runs_widget)
        self.runs_group = QGroupBox("Select Run(s)")
        group_layout = QVBoxLayout()
        group_layout.addWidget(self.runs_scroll)
        self.select_all_runs = QCheckBox("Select All Runs")
        self.select_all_runs.stateChanged.connect(self.toggle_all_runs)
        group_layout.addWidget(self.select_all_runs)
        self.runs_group.setLayout(group_layout)
        self.content_layout.addWidget(self.runs_group)

        self.selection_layout.addLayout(self.content_layout)

        # Buttons for selection tab
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

        # Graph Tab
        self.graph_tab = QWidget()
        self.graph_layout = QVBoxLayout(self.graph_tab)
        self.graph_window = None
        self.back_button = QPushButton("Back")
        self.back_button.clicked.connect(self.show_selection_tab)
        self.graph_layout.addWidget(self.back_button)

        # Add tabs to tab widget
        self.tab_widget.addTab(self.selection_tab, "Selection")
        self.tab_widget.addTab(self.graph_tab, "Graph")

        self.setLayout(self.main_layout)

        # Load and display initial data
        self.reload_data()
        self.display_data()

    def preview_file(self):
        """Preview the content of the first selected file or prompt if none selected."""
        if not self.selected_files:
            QMessageBox.warning(self, "Warning!", "No files selected to preview.")
            return

        # Read and display content of the first file
        file_path = self.selected_files[0]
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                file_content = file.read()

            # Create preview dialog
            preview_dialog = QDialog(self)
            preview_dialog.setWindowTitle(f"Preview of {os.path.basename(file_path)}")
            preview_dialog.setGeometry(250, 250, 600, 400)

            text_edit = QTextEdit(preview_dialog)
            text_edit.setReadOnly(True)
            text_edit.setPlainText(file_content)

            layout = QVBoxLayout()
            layout.addWidget(text_edit)
            preview_dialog.setLayout(layout)

            preview_dialog.exec_()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not preview the file:\n{str(e)}")

    def display_data(self):
        """Display variables and runs in their respective scroll areas."""
        # Clear existing layouts
        self.clear_layout(self.x_variables_layout)
        self.clear_layout(self.y_variables_layout)
        self.clear_layout(self.runs_layout)

        if not self.data:
            # Display placeholder labels if no  data is available
            self.x_variables_layout.addWidget(QLabel("No data available (using mock data or API down)."))
            self.y_variables_layout.addWidget(QLabel("No data available (using mock data or API down)."))
            self.runs_layout.addWidget(QLabel("No data available (using mock data or API down)."))
            return

        # Extract runs and variables from data
        runs, variables = extract_runs_and_variables(self.data)

        print(f"Runs: {runs}, Variables: {variables}")

        # Load variable mappings from DATA.CDE
        try:
            variable_map = parse_data_cde()
        except FileNotFoundError as e:
            print(f"Error loading DATA.CDE: {e}")
            QMessageBox.warning(self, "Warning", "DATA.CDE file not found. Variable names will be displayed as acronyms.")
            variable_map = {}

        # Define headers to ignore variable selection
        headers_to_ignore = {'@YEAR', 'DOY', 'DAP', 'Days after start of simulation', 'Day of Year', 'TRNO', 'DATE', 'DAS'}

        # Populate runs
        for run in runs:
            checkbox = QCheckBox(str(run))
            checkbox.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            checkbox.setStyleSheet("QCheckBox { padding: 1px; margin: 0px; }")
            self.runs_layout.addWidget(checkbox)

        # Populate X and Y variables with full name (including units) and acronym
        for var in variables:
            if var in headers_to_ignore or any(header in var for header in headers_to_ignore):
                print(f"Skipping header variable: {var}")
                continue
            full_name = variable_map.get(var, var)
            if full_name == var:
                print(f"Variable {var} not found in DATA.CDE, using acronym only.")
            display_text = f"{full_name} ({var})" if full_name != var else var
            x_checkbox = QCheckBox(display_text)
            y_checkbox = QCheckBox(display_text)
            self.x_variables_layout.addWidget(x_checkbox)
            self.y_variables_layout.addWidget(y_checkbox)

    def clear_layout(self, layout):
        """Clear all widgets from a layout.
        
        Args:
            layout: PyQt5 layout to clear.
        """
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

    def toggle_all_runs(self, state):
        """Toggle all run checkboxes based on the Select All Runs checkbox state.
        
        Args:
            state: Qt.CheckState of the Select All Runs checkbox."""
        for checkbox in self.runs_widget.findChildren(QCheckBox):
            checkbox.setChecked(state == Qt.Checked)

    def clear_all(self):
        """Uncheck all variable and run checkboxes."""
        for checkbox in self.x_variables_widget.findChildren(QCheckBox):
            checkbox.setChecked(False)
        for checkbox in self.y_variables_widget.findChildren(QCheckBox):
            checkbox.setChecked(False)
        for checkbox in self.runs_widget.findChildren(QCheckBox):
            checkbox.setChecked(False)
        self.select_all_runs.setChecked(False)

    def reload_data(self):
        """Reload data from the files and refresh the UI."""
        # Load data from files
        self.data, error = load_all_file_data(self.selected_files)
        if error:
            QMessageBox.warning(self, "Error", error)
        print(f"Loaded data: {self.data}")
        self.display_data()

    def show_graph_tab(self):
        """Prepare plot data and switch to the graph tab."""
        # Get selected runs
        selected_runs = [checkbox.text() for checkbox in self.runs_widget.findChildren(QCheckBox) if checkbox.isChecked()]
        if not selected_runs:
            QMessageBox.warning(self, "Warning!", "Please select at least one run.")
            return
        
        # Get selected X-axis variables
        x_checkboxes = self.x_variables_widget.findChildren(QCheckBox)
        selected_x_vars = [checkbox.text() for checkbox in x_checkboxes if checkbox.isChecked()]
        if not selected_x_vars:
            QMessageBox.warning(self, "Warning!", "Please select at least one X-axis variable.")
            return

        # Get Y-axis variables
        y_checkboxes = self.y_variables_widget.findChildren(QCheckBox)
        selected_y_vars = [checkbox.text() for checkbox in y_checkboxes if checkbox.isChecked()]
        if not selected_y_vars:
            QMessageBox.warning(self, "Warning!", "Please select at least one Y-axis variable.")
            return

        if not self.data:
            QMessageBox.warning(self, "Warning!", "No data available to create a graph (using mock data or API down).")
            return

        # Prepare plot data for scatter plot
        self.plot_data = []
        is_tfile = any(entry.get("file_type") == "t" for entry in self.data)

        for run in selected_runs:
            for x_var in selected_x_vars:
                for y_var in selected_y_vars:
                    if x_var == y_var:
                        continue # Skip same variable for X and Y

                    # Extract cde from display text (e.g., "Full Name (CDE)" -> CDE)
                    x_cde = x_var.split('(')[-1].strip(')') if '(' in x_var else x_var
                    y_cde = y_var.split('(')[-1].strip(')') if '(' in y_var else y_var
                    x_values = []
                    y_values = []

                    # Extract values for selected variables and run
                    for entry in self.data:
                        run_name = entry.get('run', 'Unknown')
                        if run_name != run:
                            continue

                        for variable in entry.get('values', []):
                            cde = variable.get('cde', 'Unknown')
                            if cde == x_cde:
                                values = variable.get('values', [])
                                if values:
                                    try:
                                        x_values = list(map(float, values))
                                    except ValueError as e:
                                        print(f"ValueError for {cde} in run {run}: {e}")
                                        x_values = []
                            elif cde == y_cde:
                                values = variable.get('values', [])
                                if values:
                                    try:
                                        y_values = list(map(float, values))
                                    except ValueError as e:
                                        print(f"ValueError for {cde} in run {run}: {e}")
                                        y_values = []

                    if not x_values or not y_values:
                        print(f"No valid data for {x_cde} vs {y_cde} in run {run}")
                        continue
                    
                    # Truncate to shortest lenght to ensure matching pairs
                    min_length = min(len(x_values), len(y_values))
                    x_values = x_values[:min_length]
                    y_values = y_values[:min_length]

                    self.plot_data.append((x_values, y_values, f"{x_cde} vs {y_cde} ({run})"))

        if not self.plot_data:
            QMessageBox.warning(self, "Warning!", "No valid data to plot for the selected runs and variables.")
            return

        # Validate file selection
        filename = self.selected_files[0] if self.selected_files else None
        if filename is None:
            QMessageBox.warning(self, "Warning!", "No file selected to display graph.")
            return

        # Create or update graph window
        if self.graph_window:
            self.graph_window.plot_data = self.plot_data
            self.graph_window.refresh_plot()
        else:
            self.graph_window = GraphWindow(
                self.plot_data,
                "Scatter Plot",
                self.data,
                [x.split('(')[0].strip() for x in selected_x_vars] + [y.split('(')[0].strip() for y in selected_y_vars],
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
        """Return the selected run and variables.
        
        Returns: 
            tuple: (selected runs, (selected x variables, selected y variables), data).
        """
        selected_runs = [checkbox.text() for checkbox in self.runs_widget.findChildren(QCheckBox) if checkbox.isChecked()]
        selected_x_vars = [checkbox.text() for checkbox in self.x_variables_widget.findChildren(QCheckBox) if checkbox.isChecked()]
        selected_y_vars = [checkbox.text() for checkbox in self.y_variables_widget.findChildren(QCheckBox) if checkbox.isChecked()]
        return selected_runs, (selected_x_vars, selected_y_vars), self.data

def open_scatter_var_selection(selected_files, parent=None):
    """Open the scatter variable selection dialog and return selections.
    
    Args:
        selected_files (list): List of file oaths to process.
        parent: Parent widget for the dialog.
        
    Returns: 
        tuple: (selected runs, (selected x variables, selected y variables), data) or (None(None, None), None) if rejected.
    """
    dialog = ScatterVarSelectionDialog(selected_files, parent)
    center_window_on_parent(dialog, parent)
    if dialog.exec_():
        return dialog.get_selections()
    return None, (None, None), None

def center_window_on_parent(window, parent):
    """Center the window relative to its parent or screen.
    
    Args:
        window: PyQt5 window to center.
        parent: Parent widget or None to use screen center.
    """
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
    """Run the dialog as a standalone application for testing."""
    app = QApplication(sys.argv)
    selected_files = [r"C:\DSSAT48\somefile.out", r"C:\DSSAT48\anothertfile.t"]
    run, (x_var, y_var), data = open_scatter_var_selection(selected_files)
    print("Selected Run:", run)
    print("Selected X Variable:", x_var)
    print("Selected Y Variable:", y_var)
    print("Data:", data)
    sys.exit(app.exec_())