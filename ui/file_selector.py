# C:\Users\User\Documents\Projetos\interface_Gbuild_refatorada\ui\file_selector.py
import os
import sys
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem, 
    QListWidget, QListWidgetItem, QComboBox, QPushButton, QApplication, 
    QStyle, QMessageBox, QTextEdit
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

# Relative import with module structure
try:
    from ..utils.t_files_dictionary import CROP_T_FILE_EXTENSIONS
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from utils.t_files_dictionary import CROP_T_FILE_EXTENSIONS

def find_dssat_path(default_path="C:\\DSSAT48"):
    """Attempt to find the DSSAT installation path, defaulting to C:\\DSSAT48 if not found."""
    if os.path.exists(default_path) and os.path.isdir(default_path):
        return default_path
    possible_paths = [
        "C:\\DSSAT48",
        "C:\\Program Files\\DSSAT48",
        "C:\\Program Files (x86)\\DSSAT48"
    ]
    for path in possible_paths:
        if os.path.exists(path) and os.path.isdir(path):
            return path
    return default_path

def get_file_type(filename):
    """Determine the file type based on its extension."""
    ext = os.path.splitext(filename.lower())[1]
    if ext in CROP_T_FILE_EXTENSIONS:
        return "t"
    elif ext == ".out":
        # Check if the file is evaluate.out (or variations)
        if "evaluate" in filename.lower() and filename.lower().endswith(".out"):
            return "evaluate"
        return "out"
    else:
        return "unknown"

class FileSelectorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("File Selector")
        self.setGeometry(300, 300, 800, 500)

        # Variables to store the current directory and selected files
        self.current_dir = find_dssat_path()
        self.selected_files = []

        # Main layout
        self.layout = QVBoxLayout()

        # Horizontal layout for directory and file lists (files left, directories right)
        self.h_layout = QHBoxLayout()

        # File list (left side)
        self.file_list = QListWidget()
        self.file_list.setMinimumWidth(350)
        self.file_list.setSelectionMode(QListWidget.MultiSelection)
        self.file_list.itemClicked.connect(self.on_file_clicked)
        self.h_layout.addWidget(self.file_list, 2)

        # Directory tree (right side)
        self.dir_tree = QTreeWidget()
        self.dir_tree.setHeaderLabel("Directories")
        self.dir_tree.setMinimumWidth(250)
        self.dir_tree.setColumnCount(1)
        self.dir_tree.itemClicked.connect(self.on_dir_selected)
        self.dir_tree.itemDoubleClicked.connect(self.on_dir_double_clicked)
        self.h_layout.addWidget(self.dir_tree, 1)

        self.layout.addLayout(self.h_layout)

        # Combo box for filters
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["Output files", "Alt.Output", "T-files", "Evaluation", "All files"])
        self.filter_combo.currentIndexChanged.connect(self.apply_filter)
        self.layout.addWidget(self.filter_combo)

        # OK, cancel and preview buttons
        self.button_layout = QHBoxLayout()
        self.preview_button = QPushButton("Preview")
        self.preview_button.clicked.connect(self.preview_file)
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.on_ok_clicked)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)

        self.button_layout.addStretch()
        self.button_layout.addWidget(self.preview_button)
        self.button_layout.addWidget(self.ok_button)
        self.button_layout.addWidget(self.cancel_button)
        self.layout.addLayout(self.button_layout)



        self.setLayout(self.layout)

        # Populate the directory tree with a depth limit
        self.populate_dir_tree(max_depth=2)

    def populate_dir_tree(self, max_depth=2, current_depth=0):
        self.dir_tree.clear()
        root = QTreeWidgetItem(self.dir_tree, [os.path.basename(self.current_dir) or self.current_dir])
        root.setData(0, Qt.UserRole, self.current_dir)
        root.setIcon(0, QApplication.style().standardIcon(QStyle.SP_DirIcon))
        if current_depth < max_depth:
            self.add_subdirectories(root, self.current_dir, max_depth, current_depth + 1)
        self.dir_tree.expandItem(root)
        self.load_files()

    def add_subdirectories(self, parent_item, dir_path, max_depth, current_depth):
        try:
            for item in os.listdir(dir_path):
                full_path = os.path.join(dir_path, item)
                if os.path.isdir(full_path):
                    child = QTreeWidgetItem(parent_item, [item])
                    child.setData(0, Qt.UserRole, full_path)
                    child.setIcon(0, QApplication.style().standardIcon(QStyle.SP_DirIcon))
                    if current_depth < max_depth:
                        self.add_subdirectories(child, full_path, max_depth, current_depth + 1)
        except PermissionError:
            pass

    def on_dir_selected(self, item, column):
        self.current_dir = item.data(0, Qt.UserRole)
        self.load_files()

    def on_dir_double_clicked(self, item, column):
        self.current_dir = item.data(0, Qt.UserRole)
        self.load_files()

    def load_files(self):
        self.file_list.clear()
        if not self.current_dir:
            return
        files = [f for f in os.listdir(self.current_dir) if os.path.isfile(os.path.join(self.current_dir, f))]
        for file in files:
            item = QListWidgetItem(file)
            item.setData(Qt.UserRole, os.path.join(self.current_dir, file))
            self.file_list.addItem(item)
        self.apply_filter()

    def on_file_clicked(self, item):
        self.selected_files = [item.data(Qt.UserRole) for item in self.file_list.selectedItems()]

    def apply_filter(self):
        filter_option = self.filter_combo.currentText()
        self.file_list.clear()
        files = [f for f in os.listdir(self.current_dir) if os.path.isfile(os.path.join(self.current_dir, f))]
        
        # Debug: Print all files and their types
        print(f"Files in {self.current_dir}:")
        for f in files:
            print(f"  {f}: {get_file_type(f)}")
        
        filtered_files = []
        if filter_option == "Output files":
            filtered_files = [f for f in files if get_file_type(f) == "out"]
        elif filter_option == "Alt.Output":
            filtered_files = [f for f in files if f.endswith(".ALT")]
        elif filter_option == "T-files":
            filtered_files = [f for f in files if get_file_type(f) == "t"]
        elif filter_option == "Evaluation":
            filtered_files = [f for f in files if get_file_type(f) == "evaluate"]
        else:  # All files
            filtered_files = files

        print(f"Filtered files for {filter_option}: {filtered_files}")
        for file in filtered_files:
            item = QListWidgetItem(file)
            item.setData(Qt.UserRole, os.path.join(self.current_dir, file))
            self.file_list.addItem(item)

    def on_ok_clicked(self):
        if not self.selected_files:
            QMessageBox.warning(self, "No Files Selected", "Please select at least one file before proceeding.")
            return
        self.accept()

    def get_selected_files(self):
        return self.selected_files
    
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
            preview_dialog.resize(600, 400)

            text_edit = QTextEdit(preview_dialog)
            text_edit.setReadOnly(True)
            text_edit.setPlainText(file_content)

            layout = QVBoxLayout()
            layout.addWidget(text_edit)
            preview_dialog.setLayout(layout)

            # Centralizar o preview
            center_window_on_parent(preview_dialog, self)
            preview_dialog.exec_()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not preview the file:\n{str(e)}")



def open_file_selector(parent=None):
    """Open the file selector dialog and return the selected files."""
    dialog = FileSelectorDialog(parent)
    center_window_on_parent(dialog, parent)
    if dialog.exec_():
        return dialog.get_selected_files()
    return []

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
    files = open_file_selector()
    print("Selected files:", files)
    sys.exit(app.exec_())