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
    from ..utils.cde_data_parser import parse_data_cde
    from ..data.data_processor import load_all_file_data, extract_runs_and_variables, get_file_type
    from ..plots.plotting import plot_time_series
    from ..ui.graph_window import GraphWindow
except ImportError:
    # Add project root to sys.path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    sys.path.insert(0, project_root)
    from data.data_processor import load_all_file_data, extract_runs_and_variables, get_file_type
    from utils.cde_data_parser import parse_data_cde
    from plots.plotting import plot_time_series
    from ui.graph_window import GraphWindow
    
class TimeSeriesVarSelectionDialog(QDialog):
    def __init__(self, selected_files, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Time Series Variable and Run Selection")
        self.setGeometry(200, 200, 1000, 700)  # Adjusted size to accommodate tabs

        # Store the selected files
        self.selected_files = selected_files
        self.data = []
        self.plot_data = []

        # Validate file selection: max one .t file
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

        # Horizontal layout for variables and runs
        self.content_layout = QHBoxLayout()


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

        # Horizontal layout for variables and runs
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

        #Runs
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

        file_path = self.selected_files[0]
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                file_content = file.read()

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
        self.clear_layout(self.variables_layout)
        self.clear_layout(self.runs_layout)

        if not self.data:
            self.variables_layout.addWidget(QLabel("No data available (using mock data or API down)."))
            self.runs_layout.addWidget(QLabel("No data available (using mock data or API down)."))
            return

        runs, variables = extract_runs_and_variables(self.data)

        print(f"Runs: {runs}, Variables: {variables}")

        # Load variable mappings from DATA.CDE
        try:
            variable_map = parse_data_cde()
        except FileNotFoundError as e:
            print(f"Error loading DATA.CDE: {e}")
            QMessageBox.warning(self, "Warning", "DATA.CDE file not found. Variable names will be displayed as acronyms.")
            variable_map = {}

        # Define headers to ignore (include DAS and its forms)
        headers_to_ignore = {'@YEAR', 'DOY', 'DAP', 'Days after start of simulation', 'Day of Year', 'TRNO', 'DATE', 'DAS'}

        # Populate runs
        for run in runs:
            checkbox = QCheckBox(str(run))
            checkbox.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            checkbox.setStyleSheet("QCheckBox { padding: 1px; margin: 0px; }")
            self.runs_layout.addWidget(checkbox)

        # Populate variables with full name (including units) and acronym, excluding headers
        for var in variables:
            # Check if var is an acronym or full text contains a header
            if var in headers_to_ignore or any(header in var for header in headers_to_ignore):
                print(f"Skipping header variable: {var}")
                continue
            full_name = variable_map.get(var, var)
            if full_name == var:
                print(f"Variable {var} not found in DATA.CDE, using acronym only.")
            display_text = f"{full_name} ({var})" if full_name != var else var
            checkbox = QCheckBox(display_text)
            self.variables_layout.addWidget(checkbox)
                
    def clear_layout(self, layout):
        """Clear all widgets from a layout."""
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def toggle_all_runs(self, state):
        """Toggle all run checkboxes based on the Select All Runs checkbox."""
        for checkbox in self.runs_widget.findChildren(QCheckBox):
            checkbox.setChecked(state == Qt.Checked)

    def clear_all(self):
        """Clear all selections for variables and runs."""
        for checkbox in self.variables_widget.findChildren(QCheckBox):
            checkbox.setChecked(False)
        for checkbox in self.runs_widget.findChildren(QCheckBox):
            checkbox.setChecked(False)
        self.select_all_runs.setChecked(False)

    def reload_data(self):
        """Reload data from the files and refresh the UI."""
        self.data, error = load_all_file_data(self.selected_files)
        if error:
            QMessageBox.warning(self, "Warning!", error)
        print(f"Loaded data: {self.data}")

    def show_graph_tab(self):
        """Prepare plot data and switch to the graph tab."""
        selected_runs = [checkbox.text() for checkbox in self.runs_widget.findChildren(QCheckBox) if checkbox.isChecked()]
        selected_vars = [checkbox.text() for checkbox in self.variables_widget.findChildren(QCheckBox) if checkbox.isChecked()]

        if not self.data:
            QMessageBox.warning(self, "Warning!", "No data available to create a graph (using mock data or API down).")
            return
        if not selected_runs or not selected_vars:
            QMessageBox.warning(self, "Warning!", "Select at least one run and one variable")
            return

        # Prepare plot data
        self.plot_data = []
        is_tfile = any(entry.get("file_type") == "t" for entry in self.data)

        for entry in self.data:
            run_name = entry.get('run', 'Unknown')
            if run_name not in selected_runs:
                continue

            for variable in entry.get('values', []):
                cde = variable.get('cde', 'Unknown')
                # Match cde with selected_vars (handle both "DESCRIPTION (CDE)" and "CDE" formats)
                if any(cde in var or f"({cde})" in var for var in selected_vars):
                    values = variable.get('values', [])
                    if not values:
                        print(f"Warning: No values for {cde} in run {run_name}")
                        continue

                    try:
                        y_values = list(map(float, values))

                        if is_tfile:
                            day_str = entry.get('day', '')
                            try:
                                start_date = datetime.strptime(day_str, '%Y-%m-%d')
                                x_values = [start_date + timedelta(days=i) for i in range(len(y_values))]
                            except (ValueError, TypeError) as e:
                                print(f"Invalid or missing 'day' in .t file for {run_name}: {day_str}. Error: {e}")
                                x_values = list(range(len(y_values)))

                            self.plot_data.append({
                                'x_calendar': x_values,
                                'x_dap': list(range(len(y_values))),
                                'y': y_values,
                                'label': f'{cde} ({run_name})'
                            })
                        else:
                            year_var = next((v for v in entry['values'] if v['cde'].upper() == '@YEAR'), None)
                            doy_var = next((v for v in entry['values'] if v['cde'].upper() == 'DOY'), None)
                            dap_var = next((v for v in entry['values'] if v['cde'].upper() == 'DAP'), None)

                            calendar_x = []
                            dap_x = []

                            if year_var and doy_var:
                                try:
                                    calendar_x = [
                                        datetime.strptime(f"{y}-{int(d):03}", "%Y-%j")
                                        for y, d in zip(year_var['values'], doy_var['values'])
                                    ]
                                except Exception as e:
                                    print(f"Error converting YEAR+DOY to dates for {run_name}: {e}")
                                    calendar_x = list(range(len(y_values)))

                            if dap_var:
                                try:
                                    dap_x = list(map(int, dap_var['values']))
                                except Exception as e:
                                    print(f"Error parsing DAP values for {run_name}: {e}")
                                    dap_x = list(range(len(y_values)))
                            else:
                                dap_x = list(range(len(y_values)))

                            self.plot_data.append({
                                'x_calendar': calendar_x,
                                'x_dap': dap_x,
                                'y': y_values,
                                'label': f'{cde} ({run_name})'
                            })
                    except ValueError as e:
                        print(f"ValueError for {cde} in run {run_name}: {e}")
                        continue

        print(f"Generated plot_data: {self.plot_data}")  # Debug print
        filename = self.selected_files[0] if self.selected_files else None
        if filename is None:
            QMessageBox.warning(self, "Warning!", "No file selected to display graph.")
            return

        # Create or update the Graph Window
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