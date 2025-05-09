import sys
import os
import json
import subprocess
import requests
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import (QApplication, QMainWindow, QListWidgetItem, QFileDialog, 
                             QMessageBox, QVBoxLayout, QLabel, QListWidget, QPushButton, 
                             QWidget, QCheckBox, QGroupBox, QScrollArea, QSizePolicy, 
                             QDialog, QRadioButton, QButtonGroup, QFormLayout, QTextEdit)
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
from collections import defaultdict

CROP_T_FILE_EXTENSIONS = {
    '.alt': 'Alfalfa/Lucerna',
    '.art': 'Aroid',
    '.bat': 'Barley',
    '.bnt': 'Dry bean',
    '.bwt': 'Broad leaf weeds',
    '.cot': 'Cotton',
    '.cst': 'Cassava',
    '.fat': 'Fallow',
    '.gwt': 'Grass-weeds',
    '.mlt': 'Pearl millet',
    '.mzt': 'Maize/Corn',
    '.pnt': 'Peanut',
    '.ptt': 'Potato',
    '.rit': 'Rice',
    '.sbt': 'Soybean',
    '.sct': 'Sugar cane',
    '.sgt': 'Sorghum',
    '.stt': 'Shrubs/Trees',
    '.wht': 'Wheat'
}

def plot_graph(figure, plot_data, plot_type):
    figure.clear()
    ax = figure.add_subplot(111)

    for data in plot_data:
        if plot_type == "time series":
            ax.plot(data['x'], data['y'], label=data['label'])
        elif plot_type == "scatter":
            ax.scatter(data['x'], data['y'], label=data['label'])

    ax.set_xlabel('Time')
    ax.set_ylabel('Value')
    ax.legend()
    ax.grid(True)


def print_graph(canvas, parent):
    printer = QPrinter(QPrinter.HighResolution)
    dialog = QPrintDialog(printer, parent)
    if dialog.exec_() == QDialog.Accepted:
        canvas.print_(printer)

def export_data_to_txt_time_series(plot_data, parent):
    options = QFileDialog.Options()
    file_path, _ = QFileDialog.getSaveFileName(parent, "Save Variables to TXT", "", "Text Files (*.txt);;All Files (*)", options=options)
    if file_path:
        max_days = max(len(dataset['y']) for dataset in plot_data)

        df = pd.DataFrame({'Day': range(1, max_days + 1)})
        run_names = defaultdict(list)

        for dataset in plot_data:
            label = dataset.get('label', 'No label')
            values = dataset.get('y', [])
            values += [None] * (max_days - len(values))
            run = label.split('(')[-1].strip(')')
            run_names[run].append(label)
            df[label] = values

        new_columns = {}
        for i, run in enumerate(run_names.keys(), start=1):
            for var_name in run_names[run]:
                new_columns[var_name] = f"{var_name.split(' ')[0]} (Run {i})"
        df.rename(columns=new_columns, inplace=True)

        column_widths = {col: max(len(col), df[col].astype(str).map(len).max()) for col in df.columns}

        with open(file_path, 'w') as f:
            header = '\t'.join(col.ljust(column_widths[col]) for col in df.columns)
            f.write(header + '\n')
            for index, row in df.iterrows():
                line = '\t'.join(str(item).ljust(column_widths[col]) if item is not None else ' ' * column_widths[col] for col, item in zip(df.columns, row))
                f.write(line + '\n')

def export_data_to_excel_times_series(plot_data, parent):
    options = QFileDialog.Options()
    file_path, _ = QFileDialog.getSaveFileName(parent, "Save Data to Excel", "", "Excel Files (*.xlsx);;All Files (*)", options=options)
    if file_path:
        with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
            df = pd.DataFrame()
            for dataset in plot_data:
                label = dataset.get('label', 'No label')
                values = dataset.get('y', [])
                df[label] = values

            df.to_excel(writer, sheet_name='Data', index=False, startrow=1)
            workbook = writer.book
            worksheet = writer.sheets['Data']

            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value)

            chart_sheet = workbook.add_worksheet('Charts')
            chart = workbook.add_chart({'type': 'line'})

            for i, col in enumerate(df.columns):
                chart.add_series({
                    'name': col,
                    'values': f'Data!${chr(65 + i)}$2:${chr(65 + i)}${len(df) + 1}'
                })

            chart.set_title({'name': 'Graph Title'})
            chart.set_x_axis({'name': 'X-axis'})
            chart.set_y_axis({'name': 'Y-axis'})
            chart_sheet.insert_chart('B2', chart, {'x_offset': 25, 'y_offset': 10, 'x_scale': 2, 'y_scale': 1.5})

            for i in range(len(df.columns)):
                chart_sheet.set_column(i, i, 0)

def export_data_to_txt_scatter(plot_data, parent):
    options = QFileDialog.Options()
    file_path, _ = QFileDialog.getSaveFileName(parent, "Save Scatter Plot Data to TXT", "", "Text Files (*.txt);;All Files (*)", options=options)
    if file_path:
        with open(file_path, 'w') as f:
            f.write("Scatter Plot Data\n")
            f.write("X Variable\tY Variable\tRun\n")
            for x_values, y_values, label in plot_data:
                f.write(f"{label}\n")
                f.write("X\tY\n")
                for x, y in zip(x_values, y_values):
                    f.write(f"{x}\t{y}\n")
                f.write("\n")

def export_data_to_excel_scatter(plot_data, parent):
    options = QFileDialog.Options()
    file_path, _ = QFileDialog.getSaveFileName(parent, "Save Scatter Plot Data & Graph to Excel", "", "Excel Files (*.xlsx);;All Files (*)", options=options)
    if file_path:
        with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
            df = pd.DataFrame()
            for idx, (x_values, y_values, label) in enumerate(plot_data):
                data_df = pd.DataFrame({
                    'X': x_values,
                    'Y': y_values
                })
                sheet_name = f"Data {idx+1}"
                data_df.to_excel(writer, sheet_name=sheet_name, index=False)

            workbook = writer.book
            chart_sheet = workbook.add_worksheet('Scatter Plot Graphs')

            for idx, (x_values, y_values, label) in enumerate(plot_data):
                chart = workbook.add_chart({'type': 'scatter'})

                sheet_name = f"Data {idx+1}"
                chart.add_series({
                    'name': label,
                    'categories': f"'{sheet_name}'!$A$2:$A${len(x_values) + 1}",  
                    'values': f"'{sheet_name}'!$B$2:$B${len(y_values) + 1}",      
                    'marker': {'type': 'circle', 'size': 5}                       
                })

                chart.set_title({'name': f'Scatter Plot - {label}'})
                chart.set_x_axis({'name': 'X Variable'})
                chart.set_y_axis({'name': 'Y Variable'})

                chart_sheet.insert_chart(f'B{2 + 15 * idx}', chart, {'x_offset': 25, 'y_offset': 10, 'x_scale': 1.5, 'y_scale': 1.5})



def select_directory(self, current_directory, load_files_callback):
    directory = QFileDialog.getExistingDirectory(self, "Select Directory", current_directory)
    if directory:
        load_files_callback(directory)
        return directory
    return current_directory

def load_files(self, directory, extension, list_files_callback):
    if not os.path.exists(directory):
        QMessageBox.warning(self, "Warning!", "Directory not found")
        self.listWidget.clear()
        return
    list_files_callback(directory, extension)

def list_files(self, directory, extension):
    self.listWidget.clear()
    files_found = False
    
    valid_t_extensions = CROP_T_FILE_EXTENSIONS.keys()
    
    for file_name in os.listdir(directory):
        file_ext = os.path.splitext(file_name)[1].lower()
        
        if (file_name.upper().endswith(extension.upper()) or
            file_ext in valid_t_extensions):
            files_found = True
            file_path = os.path.join(directory, file_name)
            item = QListWidgetItem(file_name)
            item.setData(1, file_path)
            self.listWidget.addItem(item)
    
    if not files_found:
        self.listWidget.addItem("No files found")

def preview_file(self):
    current_item = self.listWidget.currentItem()
    if not current_item:
        QMessageBox.warning(self, "Warning!", "No file selected.")
        return

    file_path = current_item.data(1)
    
    if not os.path.isfile(file_path):
        QMessageBox.warning(self, "Error", f"File not found: {file_path}")
        return

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            file_content = file.read()

        preview_dialog = QDialog(self)
        preview_dialog.setWindowTitle("Preview of " + current_item.text())
        preview_dialog.setGeometry(200, 200, 600, 400)

        text_edit = QTextEdit(preview_dialog)
        text_edit.setReadOnly(True)
        text_edit.setPlainText(file_content)

        layout = QVBoxLayout()
        layout.addWidget(text_edit)
        preview_dialog.setLayout(layout)

        preview_dialog.exec_()

    except Exception as e:
        QMessageBox.critical(self, "Error", f"Could not preview the file:\n{str(e)}")

def open_file(self):
    current_items = self.listWidget.selectedItems()
    if not current_items:
        QMessageBox.warning(self, "Warning!", "No file selected")
        return

    self.data = []  
    for item in current_items:
        file_name = item.text()
        file_path = item.data(1)
        file_ext = os.path.splitext(file_name)[1].lower()

        if file_ext in CROP_T_FILE_EXTENSIONS:
            crop_type = CROP_T_FILE_EXTENSIONS[file_ext]
            url = f"http://localhost:3000/api/t/{crop_type}/{file_name}"
        elif file_name.lower().endswith('.out'):
            crop_name = os.path.basename(self.current_directory)
            url = f"http://localhost:3000/api/out/{crop_name}/{file_name}"
        else:
            QMessageBox.warning(self, "Warning!", f"Unsupported file type: {file_name}")
            continue

        try:
            print(f"Requesting URL: {url}")
            response = requests.get(url)
            response.raise_for_status()

            if response.text.strip() == "":
                QMessageBox.warning(self, "Error", f"No data returned for file: {file_name}")
                continue

            file_data = response.json()

            if file_data is None:
                QMessageBox.warning(self, "Error", f"Invalid response for file: {file_name}")
                continue

            self.data.extend(file_data)
            print("API Response:", file_data)

            data_by_day = defaultdict(dict)
            variables_set = set()

            for entry in file_data:
                print("Entry:", entry)
                if isinstance(entry, dict):
                    day = entry.get('day')
                    run = entry.get('run')
                    variables = {var['cde']: var for var in entry.get('values', [])}
                    data_by_day[day][run] = variables
                    variables_set.update(variables.keys())
                else:
                    print(f"Warning: Unexpected entry format: {entry}")

            print("Processed data:", data_by_day)

        except requests.RequestException as e:
            QMessageBox.warning(self, "Error", f"Error accessing the API for file {file_name}: {str(e)}")

    self.display_data()


def graph_time_series(figure, plot_data, file_extension):
    figure.clear()
    ax = figure.add_subplot(111)
    
    for data in plot_data:
        if len(data['x']) == 1 and len(data['y']) > 1:
            x_values = list(range(1, len(data['y']) + 1))
        else:
            x_values = data['x']
            
        if file_extension.lower() == '.t' or len(file_extension) == 3: 
            ax.plot(x_values, data['y'], 'o', label=data['label'])
        else:  
            ax.plot(x_values, data['y'], label=data['label'])  
    
    ax.set_xlabel('Time')
    ax.set_ylabel('Value')
    ax.legend()
    ax.grid(True)
    figure.canvas.draw()
    
def graph_scatter(figure, plot_data):
    figure.clear()
    ax = figure.add_subplot(111)
    
    for x_values, y_values, label in plot_data:
        ax.scatter(x_values, y_values, label=label)
    
    ax.set_xlabel('X-Axis Variable')
    ax.set_ylabel('Y-Axis Variable')
    ax.legend()
    figure.canvas.draw()
    
def set_new_window(window_class, current_window, *args, **kwargs):
    close_previous_window(current_window)

    new_window = window_class(*args, **kwargs)
    new_window.show()

    return new_window

def close_previous_window(current_window):
    if current_window is not None:
        current_window.close()  
        current_window.deleteLater()
def close_time_series(window_instance):
    if window_instance is not None:
        window_instance.close()
def close_scatter_plot(window_instance):
    if window_instance is not None:
        window_instance.close()
def close_evaluate(current_window):
    if current_window is not None:
        current_window.close()
        current_window.deleteLater()
