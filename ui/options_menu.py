from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QPushButton, QMessageBox, QCheckBox
from PyQt5.QtCore import Qt

class OptionsDialog(QDialog):
    """Dialog for selecting the plot type the DSSAT Output Viewer."""
    def __init__(self, parent=None):
        """Initialize the options dialog with a tree widget for plot type selection.
        
        Args:
            parent: Parent widget for the dialog (typically MainWindow).
        """
        super().__init__(parent)
        # Set dialog properties
        self.setWindowTitle("Options")
        self.setGeometry(200, 200, 300, 200)
        self.parent_window = parent  # Reference to MainWindow
        self.plot_type = "time_series"  # Default plot type

        # Main layout
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Collapsible tree widget for plot types
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderHidden(True)  # No header for a cleaner look
        self.tree_widget.setStyleSheet("""
            QTreeWidget {
                font: 10pt "Arial";
                background-color: #f0f0f0;
                border: 1px solid #d3d3d3;
            }
            QTreeWidget::item {
                padding: 5px;
            }
            QTreeWidget::item:selected {
                background-color: #d3d3d3;
                color: black;
            }
        """)  # Matches current UI styling

        # Checkbox for Simulated vs Measured Data
        self.sim_vs_meas_checkbox = QCheckBox("Simulated vs Measured Data")
        self.sim_vs_meas_checkbox.setVisible(False)
        layout.addWidget(self.sim_vs_meas_checkbox)

        # Add plot types as top-level items
        self.time_series_item = QTreeWidgetItem(self.tree_widget, ["Time Series"])
        self.scatter_plot_item = QTreeWidgetItem(self.tree_widget, ["Scatter Plot"])
        self.evaluate_item = QTreeWidgetItem(self.tree_widget, ["Evaluate"])

        # Set initial selection to Time Series
        self.tree_widget.setCurrentItem(self.time_series_item)
        self.time_series_item.setSelected(True)

        layout.addWidget(self.tree_widget)
        self.tree_widget.itemSelectionChanged.connect(self.on_selection_changed)

        # Apply button
        self.apply_button = QPushButton("Apply", self)
        self.apply_button.clicked.connect(self.apply)
        self.apply_button.setStyleSheet("""
            QPushButton {
                font: 10pt "Arial";
                background-color: #4CAF50;
                color: white;
                padding: 5px;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)  # Consistent with UI buttons
        layout.addWidget(self.apply_button)

    def on_selection_changed(self):
        """Show/hide the Simulated vs Measured checkbox based on Scatter Plot selection."""
        selected = self.tree_widget.selectedItems()
        if selected and selected[0] == self.scatter_plot_item:
            self.sim_vs_meas_checkbox.setVisible(True)
        else:
            self.sim_vs_meas_checkbox.setVisible(False)
            self.sim_vs_meas_checkbox.setChecked(False)

    def apply(self):
        """Apply the selected plot type and close the dialog if valid."""
        selected_item = self.tree_widget.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Warning", "Please select a plot type.")
            return
        new_plot_type = selected_item.text(0).lower().replace(" ", "_")
        if new_plot_type == "scatter_plot" and self.sim_vs_meas_checkbox.isChecked():
            new_plot_type = "scatter_sim_vs_meas"
        if new_plot_type == self.plot_type:
            self.accept()  # No change, close dialog
            return
        self.plot_type = new_plot_type
        self.accept()  # Update plot type and close dialog

    def get_plot_type(self):
        """Return the currently selected plot type, accounting for Simulated vs Measured mode.
        
        Returns:
            str: Selected plot type (lowercase with underscores, e.g., "time_series" or "scatter_sim_vs_meas").
        """
        selected_item = self.tree_widget.currentItem()
        if selected_item and selected_item == self.scatter_plot_item and self.sim_vs_meas_checkbox.isChecked():
            return "scatter_sim_vs_meas"
        return selected_item.text(0).lower().replace(" ", "_") if selected_item else self.plot_type

if __name__ == "__main__":
    """Run the dialog as a standalone application for testing."""
    from PyQt5.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    dialog = OptionsDialog()
    dialog.show()
    sys.exit(app.exec_())