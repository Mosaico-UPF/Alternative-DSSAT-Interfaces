import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QScrollArea, QCheckBox,
    QPushButton, QMessageBox, QWidget, QTextEdit, QListWidget, QSizePolicy, QTabWidget,
    QApplication, QLabel
)
from PyQt5.QtCore import Qt

# Adjust imports to handle both package and script execution
try:
    from data.data_processor import load_all_file_data, extract_runs_and_variables, get_file_type
    from plots.plotting import plot_evaluate
    from ui.graph_window import GraphWindow
except ImportError:
    # Add project root to sys.path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    sys.path.insert(0, project_root)
    from data.data_processor import load_all_file_data, extract_runs_and_variables, get_file_type
    from ui.graph_window import GraphWindow
    
class EvaluateVarSelectionDialog(QDialog):
    def __init__(self, selected_files, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Evaluate Variable Selection")
        self.setGeometry(200, 200, 800, 600)

        self.selected_files = selected_files
        self.data = []
        self.plot_data = []

        # Validate file selection
        eval_file_count = sum(1 for f in selected_files if get_file_type(os.path.basename(f)) == "evaluate")
        if eval_file_count == 0:
            QMessageBox.warning(self, "Warning!", "Please select at least one evaluate.out file.")
            self.reject()
            return

        # Main layout and tab widget
        self.main_layout = QVBoxLayout()
        self.tab_widget = QTabWidget()
        self.main_layout.addWidget(self.tab_widget)

        # Selection tab
        self.selection_tab = QWidget()
        self.selection_layout = QVBoxLayout(self.selection_tab)

        # Top layout with file list and preview button
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

        # Variables selection
        self.variables_group = QGroupBox("Select Variables")
        self.variables_layout = QVBoxLayout()
        self.variables_scroll = QScrollArea()
        self.variables_scroll.setWidgetResizable(True)
        self.variables_widget = QWidget()
        self.variables_widget.setLayout(self.variables_layout)
        self.variables_scroll.setWidget(self.variables_widget)
        self.variables_group.setLayout(QVBoxLayout())
        self.variables_group.layout().addWidget(self.variables_scroll)
        self.selection_layout.addWidget(self.variables_group)

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
        self.graph_window = None
        self.back_button = QPushButton("Back")
        self.back_button.clicked.connect(self.show_selection_tab)
        self.graph_layout.addWidget(self.back_button)

        # Add tabs to tab widget
        self.tab_widget.addTab(self.selection_tab, "Selection")
        self.tab_widget.addTab(self.graph_tab, "Graph")

        self.setLayout(self.main_layout)

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
        """Display the variable checkboxes based on the current data."""
        self.clear_layout(self.variables_layout)

        if not self.data:
            return

        _, variables = extract_runs_and_variables(self.data)

        seen = set()
        unique_vars = []
        for var in sorted(variables):
            if var not in seen:
                unique_vars.append(var)
                seen.add(var)

        self.variables_layout = QVBoxLayout()
        self.variables_widget = QWidget()
        self.variables_widget.setLayout(self.variables_layout)

        for var in unique_vars:
            checkbox = QCheckBox(var)
            self.variables_layout.addWidget(checkbox)

        self.variables_layout.addStretch()
        self.variables_scroll.setWidget(self.variables_widget)


    def clear_layout(self, layout):
        if layout is None:
            return

        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else:
                sub_layout = item.layout()
                if sub_layout is not None:
                    self.clear_layout(sub_layout)


    def clear_all(self):
        """Clear all variable selections."""
        for checkbox in self.variables_widget.findChildren(QCheckBox):
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
        selected_vars = [checkbox.text() for checkbox in self.variables_widget.findChildren(QCheckBox) if checkbox.isChecked()]

        if not self.data:
            QMessageBox.warning(self, "Warning!", "No data available to create a graph (using mock data or API down).")
            return
        if not selected_vars:
            QMessageBox.warning(self, "Warning!", "Select at least one variable")
            return

        # Prepare plot data, using simulated as x and measured as y
        self.plot_data = []

        # Aggregate values for each variable across runs
        all_values = defaultdict(lambda: {'simulated': [], 'measured': []})
        for entry in self.data:
            values = entry.get('values', {})
            for cde, value_dict in values.items():
                if value_dict['type'] == 'combined':
                    all_values[cde]['simulated'].append(value_dict['simulated'])
                    all_values[cde]['measured'].append(value_dict['measured'])

        # Process each selected variable
        for cde in selected_vars:
            if cde in all_values:
                x_simulated = [x for x in all_values[cde]['simulated'] if x is not None]
                y_measured = [y for y in all_values[cde]['measured'] if y is not None]
                # Fallback to simulated if no measured data
                if not y_measured and x_simulated:
                    y_measured = x_simulated[:len(x_simulated)]
                if x_simulated or y_measured:  # Plot if either is available
                    self.plot_data.append({
                        'x': x_simulated if x_simulated else y_measured,  # Use simulated or measured as x
                        'y': y_measured if y_measured else x_simulated,   # Use measured or simulated as y
                        'y_expected': y_measured if y_measured else x_simulated,
                        'label': f'{cde} (Simulated vs Measured)'
                    })
                else:
                    print(f"Warning: No valid data for {cde}")

        filename = self.selected_files[0] if self.selected_files else None
        if filename is None:
            QMessageBox.warning(self, "Warning!", "No file selected to display graph.")
            return

        # Create or update the GraphWindow
        if self.plot_data:
            if self.graph_window is None:
                self.graph_window = GraphWindow(
                    self.plot_data,
                    "Evaluate Data",
                    self.data,
                    selected_vars,
                    [],
                    filename,
                    self
                )
                self.graph_layout.addWidget(self.graph_window)
            else:
                self.graph_window.plot_data = self.plot_data
                self.graph_window.refresh_plot()

            self.tab_widget.setCurrentIndex(1)
        else:
            QMessageBox.warning(self, "Warning!", "No valid data to create a graph.")

    def show_selection_tab(self):
        """Switch back to the selection tab."""
        self.tab_widget.setCurrentIndex(0)

    def get_selections(self):
        """Return the selected variables."""
        selected_vars = [checkbox.text() for checkbox in self.variables_widget.findChildren(QCheckBox) if checkbox.isChecked()]
        return selected_vars, self.data

def open_evaluate_var_selection(selected_files, parent=None):
    """Open the evaluate variable selection dialog and return the selections."""
    dialog = EvaluateVarSelectionDialog(selected_files, parent)
    if dialog.exec_():
        return dialog.get_selections()
    return None, None

if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    selected_files = [r"C:\DSSAT48\evaluate.out"]
    vars, data = open_evaluate_var_selection(selected_files)
    print("Selected Variables:", vars)
    print("Data:", data)
    sys.exit(app.exec_())