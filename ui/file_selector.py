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
    # Add project root to sys.path for script execution
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from utils.t_files_dictionary import CROP_T_FILE_EXTENSIONS


def find_dssat_path(default_path="C:\\DSSAT48"):
    """Find the default DSSAT directory or return a fallback path.
    
    Args:
        default_path (str): Default path to check first (default "C:\\DSSAT48").
    
    Returns:
        str: Valid DSSAT directory path or the default path if none found.
    """
    # Check if the default path exists and is a directory
    if os.path.exists(default_path) and os.path.isdir(default_path):
        return default_path
    # Try alternative common DSSAT installation paths
    possible_paths = [
        "C:\\DSSAT48",
        "C:\\Program Files\\DSSAT48",
        "C:\\Program Files (x86)\\DSSAT48"
    ]
    for path in possible_paths:
        if os.path.exists(path) and os.path.isdir(path):
            return path
    # Fallback to default path if none found
    return default_path


def get_file_type(filename):
    """Determine the file type based on its extension and name.
    
    Args:
        filename (str): Name of the file to check.
        
    Returns: 
        str: File type ("t", "evaluate", "out", or "unknown").
    """
    # Extract file extension
    ext = os.path.splitext(filename.lower())[1]
    # Check for T-file extensions
    if ext in CROP_T_FILE_EXTENSIONS:
        return "t"
    # Check for .out files, specifically evaluate.out
    elif ext == ".out":
        if "evaluate" in filename.lower() and filename.lower().endswith(".out"):
            return "evaluate"
        return "out"
    else:
        return "unknown"


class FileSelectorDialog(QDialog):
    """Dialog for selecting files and directories with filtering options."""
    def __init__(self, parent=None, initial_dir=None):
        """Initialize the dialog with file and directory browsing UI.
        
        Args:
            parent: Parent widget for the dialog.
            initial_dir (str):: Initial directory to display (optional).
        """
        super().__init__(parent)
        # Set dialog properties
        self.setWindowTitle("File Selector")
        self.setGeometry(300, 300, 800, 500)

        # Initialize current directory and selected files
        self.current_dir = initial_dir if initial_dir and os.path.isdir(initial_dir) else find_dssat_path()
        self.selected_files = []

        # Set up main layout
        self.layout = QVBoxLayout()
        self.h_layout = QHBoxLayout()

        # File list widget
        self.file_list = QListWidget()
        self.file_list.setMinimumWidth(350)
        self.file_list.setSelectionMode(QListWidget.MultiSelection)
        self.file_list.itemClicked.connect(self.on_file_clicked)
        self.h_layout.addWidget(self.file_list, 2)

        # Directory tree widget
        self.dir_tree = QTreeWidget()
        self.dir_tree.setHeaderLabel("Directories")
        self.dir_tree.setMinimumWidth(250)
        self.dir_tree.setColumnCount(1)
        self.dir_tree.itemClicked.connect(self.on_dir_selected)
        self.dir_tree.itemDoubleClicked.connect(self.on_dir_double_clicked)
        self.h_layout.addWidget(self.dir_tree, 1)

        self.layout.addLayout(self.h_layout)

        # Filters
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["Output files", "Alt.Output", "T-files", "Evaluation", "All files"])
        self.filter_combo.currentIndexChanged.connect(self.apply_filter)
        self.layout.addWidget(self.filter_combo)

        # Buttons
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

        # Populate directory tree with initial directory
        self.populate_dir_tree(max_depth=2, select_path=self.current_dir)

    def populate_dir_tree(self, max_depth=2, current_depth=0, select_path=None):
        """Populate the directory tree with subdirectories up to max_depth.
        
        Args:
            max_depth (int): Maximum depth to explore directories.
            current_depth (int): Current depth in the tree.
            select_path (str): Path to select in the tree (optional).
        """
        # Clear current tree
        self.dir_tree.clear()

        # Add parent directory item
        parent_dir = os.path.dirname(self.current_dir.rstrip("\\/"))
        if parent_dir and os.path.exists(parent_dir) and parent_dir != self.current_dir:
            up_item = QTreeWidgetItem([".. (Parent Directory)"])
            up_item.setData(0, Qt.UserRole, parent_dir)
            font = up_item.font(0)
            font.setItalic(True)
            up_item.setFont(0, font)
            up_item.setIcon(0, QApplication.style().standardIcon(QStyle.SP_ArrowUp))
            self.dir_tree.addTopLevelItem(up_item)

        # Current directory as root
        root = QTreeWidgetItem([os.path.basename(self.current_dir) or self.current_dir])
        root.setData(0, Qt.UserRole, self.current_dir)
        root.setIcon(0, QApplication.style().standardIcon(QStyle.SP_DirIcon))
        self.dir_tree.addTopLevelItem(root)

        # Add subdirectories if within max depth
        if current_depth < max_depth:
            self.add_subdirectories(root, self.current_dir, max_depth, current_depth + 1)

        self.dir_tree.expandItem(root)
        self.load_files()
        if select_path:
            self.select_path_in_tree(select_path)

    def add_subdirectories(self, parent_item, dir_path, max_depth, current_depth):
        """Recursively add subdirectories to the tree widget.
        
        Args: 
            parent_item Parent QTreeWidgetItem to add subdirectories to..
            dir_path (str): Directory path to scan.
            max_depth (int): Maximum depth to explore.
            current_depth (int): Current depth in tree.
        """
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

    def select_path_in_tree(self, path):
        """Select a specific path in the directory tree
        
        Args:
            path (str): Path to select.
        """
        def recurse_select(item):
            if item.data(0, Qt.UserRole) == path:
                self.dir_tree.setCurrentItem(item)
                self.current_dir = path
                self.load_files()
                return True
            for i in range(item.childCount()):
                if recurse_select(item.child(i)):
                    item.setExpanded(True)
                    return True
            return False

        root = self.dir_tree.topLevelItem(0)
        if root:
            recurse_select(root)

    def on_dir_selected(self, item, column):
        """Handle single-click selection of a directory.

        Args:
            item: Selected QTreeWidgetItem
            column: Selected column(unused).
        """
        path = item.data(0, Qt.UserRole)
        if os.path.isdir(path):
            self.current_dir = path
            self.populate_dir_tree()

    def on_dir_double_clicked(self, item, column):
        """Handle double-click on a directory to navigate into it.
        
        Args:
            item: Double-clicked QTreeWidgetItem.
            column: Selected column (unused).
        """
        path = item.data(0, Qt.UserRole)
        if os.path.isdir(path):
            self.current_dir = path
            self.populate_dir_tree()

    def load_files(self):
        """Load files from the current directory into the file list."""
        self.file_list.clear()
        if not self.current_dir:
            return

        # List all files in the current directory
        files = [f for f in os.listdir(self.current_dir) if os.path.isfile(os.path.join(self.current_dir, f))]
        for file in files:
            item = QListWidgetItem(file)
            item.setData(Qt.UserRole, os.path.join(self.current_dir, file))
            self.file_list.addItem(item)
        self.apply_filter()

    def on_file_clicked(self, item):
        """Handle file selection and update selected files list.
        
        Args:
            item: Selected QListWidgetItem.
        """
        path = item.data(Qt.UserRole)
        if os.path.isdir(path):
            self.current_dir = path
            self.populate_dir_tree()
            return
        self.selected_files = [it.data(Qt.UserRole) for it in self.file_list.selectedItems()]

    def apply_filter(self):
        """Apply the selected filter to the file list."""
        filter_option = self.filter_combo.currentText()
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            path = item.data(Qt.UserRole)
            if os.path.isdir(path):
                item.setHidden(False)
                continue
            filename = os.path.basename(path)
            file_type = get_file_type(filename)
            hide = False
            if filter_option == "Output files" and file_type != "out":
                hide = True
            elif filter_option == "Alt.Output" and not filename.endswith(".ALT"):
                hide = True
            elif filter_option == "T-files" and file_type != "t":
                hide = True
            elif filter_option == "Evaluation" and file_type != "evaluate":
                hide = True
            item.setHidden(hide)

    def on_ok_clicked(self):
        """Handle OK button click to validate and accept selections."""
        if not self.selected_files:
            QMessageBox.warning(self, "No Files Selected", "Please select at least one file before proceeding.")
            return
        self.accept()

    def get_selected_files(self):
        """Return the list of selected files.
        
        Returns:
            list: List of selected file paths.
        """
        return self.selected_files

    def preview_file(self):
        """Preview the content of the frst selected file in a dialog."""
        if not self.selected_files:
            QMessageBox.warning(self, "Warning!", "No files selected to preview.")
            return

        # Read and display the content of the first selected file
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

            center_window_on_parent(preview_dialog, self)
            preview_dialog.exec_()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not preview the file:\n{str(e)}")


def open_file_selector(parent=None, initial_dir=None):
    """Open the file selector dialog and return selected files and last directory.

    Args:
        parent: Parent widget for the dialog.
        initial_dir (str): Initial directory to display (optional).

    Returns:
        tuple: (selected files, last directory).
    
    """
    dialog = FileSelectorDialog(parent, initial_dir)
    center_window_on_parent(dialog, parent)
    if dialog.exec_():
        return dialog.get_selected_files(), dialog.current_dir
    return [], dialog.current_dir


def center_window_on_parent(window, parent):
    """Center the window relative to its parent on screen.
    
    Args:
        parent: Parent widget for the dialog.
        initial_dir (str): Intial directory to display (optional).

    Returns:
        tuple: (selected files, last directory).    
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
    files, last_dir = open_file_selector()
    print("Selected files:", files)
    print("Last dir:", last_dir)
    sys.exit(app.exec_())
