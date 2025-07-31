import os
import sys
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QScrollArea, QCheckBox,
    QPushButton, QMessageBox, QWidget, QTextEdit, QListWidget, QSizePolicy, QTabWidget,
    QApplication, QLabel
)
from PyQt5.QtCore import Qt

# Adjust imports to handle both package and script execution
try:
    from utils.cde_data_parser import parse_data_cde
    from plots.plotting import plot_time_series
    from ui.graph_window import GraphWindow
except ImportError:
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    sys.path.insert(0, project_root)
    from utils.cde_data_parser import parse_data_cde
    from plots.plotting import plot_time_series
    from ui.graph_window import GraphWindow

class TimeSeriesVarSelectionDialog(QDialog):
    """Dialog for selecting variables and runs for time series visualization."""
    def __init__(self, selected_files, parent=None):
        """Initialize the dialog with file selection and UI setup.
        
        Args:
            selected_files (list): List of file paths to process.
            parent: Parent widget for the dialog.
        """
        super().__init__(parent)
        # Set dialog properties
        self.setWindowTitle("Time Series Variable and Run Selection")
        self.setGeometry(200, 200, 1000, 700)

        # Store selected files and initialize data containers
        self.selected_files = selected_files
        self.data = []
        self.plot_data = []

        # Validate file selection
        from data.data_processor import get_file_type
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

        # Set up main layout with tab widget
        self.main_layout = QVBoxLayout()
        self.tab_widget = QTabWidget()
        self.main_layout.addWidget(self.tab_widget)

        # Create selection tab
        self.selection_tab = QWidget()
        self.selection_layout = QVBoxLayout(self.selection_tab)

        # Create top layout for file display and preview
        self.content_layout = QHBoxLayout()
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

        # Create content layout for variable and run selection
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
        self.selection_layout.addLayout(self.content_layout)

        # Set up runs selection group
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
        self.content_layout.addWidget(self.runs_group)

        self.select_all_runs = QCheckBox("Select All Runs")
        self.select_all_runs.stateChanged.connect(self.toggle_all_runs)
        group_layout.addWidget(self.select_all_runs)

        self.runs_group.setLayout(group_layout)

        # Create buttons for selection tab
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

        # Create graph tab
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

        # Read and display the content of the first file
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
        """Diplay runs and variables in their respective scroll areas."""
        from data.data_processor import extract_runs_and_variables
        self.clear_layout(self.variables_layout)
        self.clear_layout(self.runs_layout)

        if not self.data:
            # Display placeholder labels if no data is available
            self.variables_layout.addWidget(QLabel("No data available (using mock data or API down)."))
            self.runs_layout.addWidget(QLabel("No data available (using mock data or API down)."))
            return

        # Extract runs and variables from data
        runs, variables = extract_runs_and_variables(self.data)
        print(f"Runs: {runs}")
        print(f"Variables: {variables}")
        print(f"Sample data entry: {self.data[0] if self.data else 'No data'}")

        # Load variable mappings from DATA.CDE
        try:
            variable_map = parse_data_cde()
        except FileNotFoundError as e:
            print(f"Error loading DATA.CDE: {e}")
            QMessageBox.warning(self, "Warning", "DATA.CDE file not found. Variable names will be displayed as acronyms.")
            variable_map = {}

        # Define headers to ignore for variable selection
        headers_to_ignore = {'@YEAR', 'DOY', 'DAP', 'DAYS AFTER START OF SIMULATION', 'DAY OF YEAR', 'TRNO', 'DATE', 'DAS'}

        # Identify measured variables for bolding
        observed_vars = set()
        for entry in self.data:
            if not isinstance(entry, dict):
                #print(f"Skipping invalid entry: {entry}")
                continue
            for value in entry.get('values', []):
                if value.get('type') == 'measured':
                    cde = value.get('cde')
                    if cde:
                        observed_vars.add(cde.upper())
                        #print(f"Found measured variable: {cde}")

        #print(f"Observed variables: {observed_vars}")

        # Populate runs checkboxes
        for run in runs:
            checkbox = QCheckBox(str(run))
            checkbox.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            checkbox.setStyleSheet("QCheckBox { padding: 1px; margin: 0px; }")
            self.runs_layout.addWidget(checkbox)

        # Populate variable checkboxes with full names an bold measured variables
        for var in variables:
            if var.upper() in headers_to_ignore or any(header in var.upper() for header in headers_to_ignore):
                print(f"Skipping header variable: {var}")
                continue
            full_name = variable_map.get(var, var)
            display_text = f"{full_name} ({var})" if full_name != var else var

            checkbox = QCheckBox(display_text)
            if var.upper() in observed_vars:
                font = checkbox.font()
                font.setBold(True)
                checkbox.setFont(font)
                #print(f"Bolding variable: {var}")
            self.variables_layout.addWidget(checkbox)
            
    def clear_layout(self, layout):
        """Clear all widgets from a layout.
        
        Args:
            layout: PyQt5 layout to clear.
        """
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def toggle_all_runs(self, state):
        """Toggle all run checkboxes based on the Select All Runs checkbox.
        
        Args:
            state: Qt.CheckState of the Select All Runs checkbox.
        """
        for checkbox in self.runs_widget.findChildren(QCheckBox):
            checkbox.setChecked(state == Qt.Checked)

    def clear_all(self):
        """Uncheck all variable and run checkboxes."""
        for checkbox in self.variables_widget.findChildren(QCheckBox):
            checkbox.setChecked(False)
        for checkbox in self.runs_widget.findChildren(QCheckBox):
            checkbox.setChecked(False)
        self.select_all_runs.setChecked(False)

    def reload_data(self):
        """Reload data from the files and refresh the UI."""
        from data.data_processor import load_all_file_data
        self.data, error = load_all_file_data(self.selected_files)
        if error:
            QMessageBox.warning(self, "Warning!", error)
        print(f"Loaded data: {self.data}")

    def show_graph_tab(self):
        """Prepare time series plot data and switch to the graph tab."""
        # Get selected runs and variables
        selected_runs = [checkbox.text() for checkbox in self.runs_widget.findChildren(QCheckBox) if checkbox.isChecked()]
        selected_vars = [checkbox.text() for checkbox in self.variables_widget.findChildren(QCheckBox) if checkbox.isChecked()]
        if not self.data:
            QMessageBox.warning(self, "Warning!", "No data available to create a graph.")
            return
        if not selected_runs or not selected_vars:
            QMessageBox.warning(self, "Warning!", "Select at least one run and one variable")
            return

        # Prepare plot data for time series
        self.plot_data = []
        is_tfile = any(entry.get("file_type") == "t" for entry in self.data)

        # Determine planting data for DAP calculations
        planting_date = None
        for entry in self.data:
            if entry.get("file_type") == "t" and entry.get("day"):
                try:
                    planting_date = datetime.strptime(entry.get("day"), '%Y-%m-%d')
                    break
                except ValueError:
                    continue
            elif entry.get("file_type") == "out":
                year_var = next((v for v in entry['values'] if v['cde'].upper() == '@YEAR'), None)
                doy_var = next((v for v in entry['values'] if v['cde'].upper() == 'DOY'), None)
                if year_var and doy_var and year_var['values'] and doy_var['values']:
                    try:
                        planting_date = datetime.strptime(f"{year_var['values'][0]}-{int(doy_var['values'][0]):03}", "%Y-%j")
                        break
                    except (ValueError, TypeError):
                        continue

        # Process data for each run and variable
        for entry in self.data:
            run_name = entry.get('run', 'Unknown')
            if run_name not in selected_runs:
                continue
            
            # Extract x-axis data (calendar and DAP)
            year_var = next((v for v in entry['values'] if v['cde'].upper() == '@YEAR'), None)
            doy_var = next((v for v in entry['values'] if v['cde'].upper() == 'DOY'), None)
            dap_var = next((v for v in entry['values'] if v['cde'].upper() == 'DAP'), None)

            calendar_x = []
            dap_x = []

            if is_tfile:
                day_str = entry.get('day', '')
                try:
                    start_date = datetime.strptime(day_str, '%Y-%m-%d')
                    max_len = max(len(v.get('values', [])) for v in entry.get('values', []))
                    calendar_x = [start_date + timedelta(days=i) for i in range(max_len)]
                    dap_x = list(range(max_len))
                except (ValueError, TypeError) as e:
                    print(f"Invalid or missing 'day' in .t file for {run_name}: {day_str}. Error: {e}")
                    calendar_x = list(range(max_len))
                    dap_x = list(range(max_len))
            else:
                if year_var and doy_var:
                    try:
                        calendar_x = [
                            datetime.strptime(f"{y}-{int(d):03}", "%Y-%j")
                            for y, d in zip(year_var['values'], doy_var['values'])
                        ]
                    except Exception as e:
                        print(f"Error converting YEAR+DOY to dates for {run_name}: {e}")
                if dap_var:
                    try:
                        dap_x = list(map(int, dap_var['values']))
                    except Exception as e:
                        print(f"Error parsing DAP values for {run_name}: {e}")
                max_len = max(len(v.get('values', [])) for v in entry.get('values', []))
                if not calendar_x:
                    calendar_x = list(range(max_len))
                if not dap_x:
                    dap_x = list(range(max_len))

            # Process selected variables
            for variable in entry.get('values', []):
                cde = variable.get('cde', 'Unknown')
                if any(cde in var or f"({cde})" in var for var in selected_vars):
                    values = variable.get('values', [])
                    data_type = variable.get('type', 'simulated')
                    if not values:
                        print(f"Warning: No values for {cde} in run {run_name}")
                        continue
                    try:
                        y_values = [float(v) for v in values]
                        x_calendar = variable.get('x_calendar', calendar_x[:len(y_values)])
                        if data_type == 'measured' and x_calendar and planting_date:
                            try:
                                x_dap = [
                                    (datetime.strptime(date, '%Y-%m-%d') - planting_date).days
                                    if isinstance(date, str)
                                    else (date - planting_date).days
                                    for date in x_calendar
                                ]
                            except (ValueError, TypeError) as e:
                                print(f"Error calculating DAP for measured data {cde} in run {run_name}: {e}")
                                x_dap = [0] * len(y_values)
                        else:
                            x_dap = dap_x[:len(y_values)] if not variable.get('x_calendar') else dap_x[:len(y_values)]

                        if not x_calendar or not x_dap or len(x_calendar) != len(y_values):
                            print(f"Warning: Mismatched data lengths for {cde} in run {run_name}: x={len(x_calendar)}, y={len(y_values)}")
                            continue

                        self.plot_data.append({
                            'x_calendar': x_calendar,
                            'x_dap': x_dap,
                            'y': y_values,
                            'label': f'{cde} ({run_name})',
                            'type': data_type
                        })
                    except ValueError as e:
                        print(f"ValueError for {cde} in run {run_name}: {e}")
                        continue

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
                "Time Series",
                self.data,
                selected_vars,
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
        """Return the selected runs and variables.
        
        Returns:
            tuple: (selected runs, selected variables, data).
        """
        selected_runs = [checkbox.text() for checkbox in self.runs_widget.findChildren(QCheckBox) if checkbox.isChecked()]
        selected_vars = [checkbox.text() for checkbox in self.variables_widget.findChildren(QCheckBox) if checkbox.isChecked()]
        return selected_runs, selected_vars, self.data

def open_time_series_var_selection(selected_files, parent=None):
    """Open the time series variable selection dialog and return the selections.
    
    Args:
        selected_files (list): List of file paths to process.
        parent: Parent widget for the dialog.
    
    Returns: 
        tuple: (selected runs, selected variables, data) or (None, None, None) if rejected.
    """
    dialog = TimeSeriesVarSelectionDialog(selected_files, parent)
    center_window_on_parent(dialog, parent)
    if dialog.exec_():
        return dialog.get_selections()
    return None, None, None

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
    runs, vars, data = open_time_series_var_selection(selected_files)
    print("Selected Runs:", runs)
    print("Selected Variables:", vars)
    print("Data:", data)
    sys.exit(app.exec_())