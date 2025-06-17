from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QPushButton, QMessageBox
from PyQt5.QtCore import Qt

class OptionsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
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

        # Add plot types as top-level items
        self.time_series_item = QTreeWidgetItem(self.tree_widget, ["Time Series"])
        self.scatter_plot_item = QTreeWidgetItem(self.tree_widget, ["Scatter Plot"])
        self.evaluate_item = QTreeWidgetItem(self.tree_widget, ["Evaluate"])

        # Set initial selection
        self.tree_widget.setCurrentItem(self.time_series_item)
        self.time_series_item.setSelected(True)

        layout.addWidget(self.tree_widget)

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

    def apply(self):
        selected_item = self.tree_widget.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Warning", "Please select a plot type.")
            return

        new_plot_type = selected_item.text(0).lower().replace(" ", "_")
        if new_plot_type == self.plot_type:
            self.accept()
            return

        self.plot_type = new_plot_type
        self.accept()

    def get_plot_type(self):
        selected_item = self.tree_widget.currentItem()
        return selected_item.text(0).lower().replace(" ", "_") if selected_item else self.plot_type

if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    dialog = OptionsDialog()
    dialog.show()
    sys.exit(app.exec_())