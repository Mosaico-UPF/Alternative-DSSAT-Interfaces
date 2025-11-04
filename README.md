# Alternative GBuild UI

**PYQT GBuild UI** Is a project for a community built graphical interface for DSSAT's GBuild. The project is developed using the **PYQT5** framework.
The project runs a modified version of the **jDSSAT API** that can be found in the branch Alternative-JDSSAT-API of this github repository.
In order for the project to run properly the user **has** to run the **jDSSAT** in the backend and to have the DSSAT files or software installed. 
To run the jDSSAT API the standard command is:

node .\jdssat-server.js

The command should be typed in the terminal inside the root folder/directory for the API.
---

## 🧱 Directory Structure
GBuild_ui/
├── data/ → Handles data preprocessing and parsing
│ └── data_processor.py → Processes input data for UI and exports
│
├── export/ → Manages export functionality
│ └── export_functions.py → Exports processed data (Excel, txt)
│
├── plots/ → Visualization components
│ └── plotting.py → Handles graph generation and styling
│
├── ui/ → PyQt5 user interface components
│ ├── main_window.py → Application entry point (main UI)
│ ├── file_selector.py → File input dialogs
│ ├── options_menu.py → Menu and configuration widgets
│ ├── graph_window.py → Graph visualization window
│ ├── evaluate_var_selection.py → Variable evaluation and selection UI
│ ├── scatter_plot_var_selection.py → Scatter plot selection screen
│ ├── time_series_var_selection.py → Time-series selection screen
│ └── Logo.png → UI logo image
│
├── utils/ → Core utilities and helper functions
│ ├── cde_data_parser.py → Parses DSSAT CDE files in order to acquire the full name of the variables from the acronyms
│ ├── t_files_dictionary.py → Mapping for DSSAT T files
│ ├── settings.py → Configurations and constants
│ └── stats_calculator.py→ Statistical functions for results analysis
│
├── tests/ → Automated test suite (pytest)
│ ├── test_data_processor.py
│ ├── test_plotting.py
│ └── test_stats_calculator.py
│
└── requirements.txt → Dependencies for installation


---

## ⚙️ Dependencies

| Library | Purpose |
|----------|----------|
| **PyQt5** | GUI framework for building the desktop interface |
| **pandas** | Data manipulation and tabular processing |
| **numpy** | Numerical calculations |
| **matplotlib** | Visualization and plotting |
| **scipy** | Statistical and scientific utilities |
| **xlsxwriter** | Excel file export |
| **requests** | Communication with JDSSAT API |
| **pytest** | Testing framework |

Install them all using:
```bash
pip install -r requirements.txt


## 🚀 Running the Application

Navigate to the project root directory **(GBuild_ui/)** and run:

On Windows:
python -m ui.main_window

On Linux/macOS:
python3 -m ui.main_window


This will start the PyQt5 graphical interface.

## 🧪 Running Tests

The project uses pytest for unit testing.
To run all tests, execute:

pytest -v
