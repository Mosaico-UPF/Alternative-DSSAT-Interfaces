# C:\Users\User\Documents\Projetos\interface_Gbuild_refatorada\ui\scatter_plot.py
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
    from data.data_processor import load_all_file_data, extract_runs_and_variables, get_file_type
    from ui.graph_window import GraphWindow
except ImportError:
    # Add project root to sys.path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    sys.path.insert(0, project_root)
    from data.data_processor import load_all_file_data, extract_runs_and_variables, get_file_type
    from ui.graph_window import GraphWindow

class ScatterVarSelectionDialog(QDialog):
    def __init__(self, selected_files, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Scatter Plot Variable Selection Menu")
        self.setGeometry(200, 200, 1000, 700)

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
        self.runs_group = QGroupBox("Select Run(s)")
        self.runs_layout = QVBoxLayout()
        self.runs_scroll = QScrollArea()
        self.runs_scroll.setWidgetResizable(True)
        self.runs_widget = QWidget()
        self.runs_widget.setLayout(self.runs_layout)
        self.runs_scroll.setWidget(self.runs_widget)
        self.runs_group.setLayout(QVBoxLayout())
        self.runs_group.layout().addWidget(self.runs_scroll)
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
        self.clear_layout(self.x_variables_layout)
        self.clear_layout(self.y_variables_layout)
        self.clear_layout(self.runs_layout)

        if not self.data:
            self.x_variables_layout.addWidget(QLabel("No data available (using mock data or API down)."))
            self.y_variables_layout.addWidget(QLabel("No data available (using mock data or API down)."))
            self.runs_layout.addWidget(QLabel("No data available (using mock data or API down)."))
            return

        runs, variables = extract_runs_and_variables(self.data)

        print(f"Runs: {runs}, Variables: {variables}")

        # Populate runs with checkboxes (multiple selection allowed)
        for run in runs:
            checkbox = QCheckBox(str(run))
            self.runs_layout.addWidget(checkbox)

        # Populate X-axis variables with checkboxes
        for var in variables:
            checkbox = QCheckBox(var)
            self.x_variables_layout.addWidget(checkbox)

        # Populate Y-axis variables with checkboxes
        for var in variables:
            checkbox = QCheckBox(var)
            self.y_variables_layout.addWidget(checkbox)

    def clear_layout(self, layout):
        """Clear all widgets from a layout."""
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)  # Properly remove widget from parent
                widget.deleteLater()

    def clear_all(self):
        """Clear all selections for variables and runs."""
        for checkbox in self.x_variables_widget.findChildren(QCheckBox):
            checkbox.setChecked(False)
        for checkbox in self.y_variables_widget.findChildren(QCheckBox):
            checkbox.setChecked(False)
        for checkbox in self.runs_widget.findChildren(QCheckBox):
            checkbox.setChecked(False)

    def reload_data(self):
        """Reload data from the files and refresh the UI."""
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

        # Get selected Y-axis variables
        y_checkboxes = self.y_variables_widget.findChildren(QCheckBox)
        selected_y_vars = [checkbox.text() for checkbox in y_checkboxes if checkbox.isChecked()]
        if not selected_y_vars:
            QMessageBox.warning(self, "Warning!", "Please select at least one Y-axis variable.")
            return

        # Validation
        if not self.data:
            QMessageBox.warning(self, "Warning!", "No data available to create a graph (using mock data or API down).")
            return

        # Prepare plot data
        self.plot_data = []
        is_tfile = any(entry.get("file_type") == "t" for entry in self.data)

        for run in selected_runs:
            for x_var in selected_x_vars:
                for y_var in selected_y_vars:
                    if x_var == y_var:
                        continue  # Skip if X and Y variables are the same

                    x_values = []
                    y_values = []

                    for entry in self.data:
                        run_name = entry.get('run', 'Unknown')
                        if run_name != run:
                            continue

                        # Extract X and Y values for the selected variables
                        for variable in entry.get('values', []):
                            cde = variable.get('cde', 'Unknown')
                            if cde == x_var:
                                values = variable.get('values', [])
                                if values:
                                    try:
                                        x_values = list(map(float, values))
                                    except ValueError as e:
                                        print(f"ValueError for {cde}: {e}")
                                        x_values = []
                            elif cde == y_var:
                                values = variable.get('values', [])
                                if values:
                                    try:
                                        y_values = list(map(float, values))
                                    except ValueError as e:
                                        print(f"ValueError for {cde}: {e}")
                                        y_values = []

                    # Ensure X and Y have the same length
                    if not x_values or not y_values:
                        print(f"No valid data for {x_var} vs {y_var} in run {run}")
                        continue

                    min_length = min(len(x_values), len(y_values))
                    x_values = x_values[:min_length]
                    y_values = y_values[:min_length]

                    # Add scatter plot data for this X/Y pair and run
                    self.plot_data.append((x_values, y_values, f"{x_var} vs {y_var} ({run})"))

        if not self.plot_data:
            QMessageBox.warning(self, "Warning!", "No valid data to plot for the selected runs and variables.")
            return

        # Create or update GraphWindow in the graph tab
        if self.graph_window:
            self.graph_window.plot_data = self.plot_data
            self.graph_window.refresh_plot()
        else:
            self.graph_window = GraphWindow(self.plot_data, "Scatter Plot", self.data, selected_x_vars + selected_y_vars, selected_runs, self)
            self.graph_layout.addWidget(self.graph_window)
        self.tab_widget.setCurrentIndex(1)  # Switch to Graph tab

    def show_selection_tab(self):
        """Switch back to the selection tab."""
        self.tab_widget.setCurrentIndex(0)

    def get_selections(self):
        """Return the selected run and variables."""
        selected_runs = [checkbox.text() for checkbox in self.runs_widget.findChildren(QCheckBox) if checkbox.isChecked()]
        selected_x_vars = [checkbox.text() for checkbox in self.x_variables_widget.findChildren(QCheckBox) if checkbox.isChecked()]
        selected_y_vars = [checkbox.text() for checkbox in self.y_variables_widget.findChildren(QCheckBox) if checkbox.isChecked()]
        return selected_runs, (selected_x_vars, selected_y_vars), self.data

def open_scatter_var_selection(selected_files, parent=None):
    dialog = ScatterVarSelectionDialog(selected_files, parent)
    if dialog.exec_():
        return dialog.get_selections()
    return None, (None, None), None

if __name__ == "__main__":
    app = QApplication(sys.argv)
    selected_files = [r"C:\DSSAT48\somefile.out", r"C:\DSSAT48\anothertfile.t"]
    run, (x_var, y_var), data = open_scatter_var_selection(selected_files)
    print("Selected Run:", run)
    print("Selected X Variable:", x_var)
    print("Selected Y Variable:", y_var)
    print("Data:", data)
    sys.exit(app.exec_())