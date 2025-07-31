# C:\Users\User\Documents\Projetos\interface_Gbuild_refatorada\export\export_functions.py
import pandas as pd
from PyQt5.QtWidgets import QFileDialog
from collections import defaultdict
from xlsxwriter.utility import xl_col_to_name

def export_data_to_txt_time_series(plot_data, parent):
    """ Export time series data to a TXT file with simulated and measured data aligned in separate sections

    Args: 
        plot_data (list): List of datasets containing labels, y-values, and data type (simulated/measured)
        parent: Parent Widget for the QFileDialog
    """
    # Open file save dialog for TXT file
    options = QFileDialog.Options()
    file_path, _ = QFileDialog.getSaveFileName(
        parent,
        "Save Time Series to TXT",
        "",
        "Text Files (*.txt);;All Files (*)",
        options=options
    )
    if not file_path:
        return
    
    # Initialize dictionaries to store simulated and measured data
    simulated_dict = defaultdict(list)
    measured_dict = defaultdict(dict)
    max_len = 0

    # Separate data into simulated and measured dictionaries
    for dataset in plot_data:
        label = dataset.get('label', 'No label')
        y_vals = dataset.get('y', [])
        data_type = dataset.get('type', 'simulated')
        if data_type == 'simulated':
            simulated_dict[label] = y_vals
            max_len = max(max_len, len(y_vals))
        elif data_type == 'measured':
            x_vals = dataset.get('x_calendar', [])
            for x, y in zip(x_vals, y_vals):
                measured_dict[x][f"{label} (Measured)"] = y

    # Build DataFrame for simulated data, indexed by day
    df_sim = pd.DataFrame({'Day': range(1, max_len + 1)})
    for label, y_vals in simulated_dict.items():
        padded = y_vals + [None] * (max_len - len(y_vals))
        df_sim[f"{label} (Simulated)"] = padded

    # Build DataFrame for measured data, indexed by date
    df_meas = pd.DataFrame.from_dict(measured_dict, orient='index')
    df_meas.index.name = 'Date'
    df_meas.reset_index(inplace=True)
    df_meas.sort_values(by='Date', inplace=True)

    def write_aligned(df, file_obj, title):
        """Write DataFrame to a file with aligned columns
        
        Args:
            df (pd.DataFrame): DataFrame to write.
            file_obj: File object to write to.
            title (str): Section title for the output.
        """
        file_obj.write(f"=== {title} ===\n")
        # Calculate width for each column
        col_widths = {
            col: max(len(str(col)), df[col].astype(str).map(len).max())
            for col in df.columns
        }

        # Write header with aligned column names
        header_line = "  ".join(str(col).ljust(col_widths[col]) for col in df.columns)
        file_obj.write(header_line + "\n")

        # Write data rows with aligned values 
        for _, row in df.iterrows():
            line = "  ".join(
                str(row[col]).ljust(col_widths[col]) if pd.notna(row[col]) else " " * col_widths[col]
                for col in df.columns
            )
            file_obj.write(line + "\n")

    # Write both DataFrames to the TXT file
    with open(file_path, 'w', encoding='utf-8') as f:
        write_aligned(df_sim, f, "Simulated Time Series")
        f.write("\n")
        write_aligned(df_meas, f, "Measured Data Points")



def export_data_to_excel_time_series(plot_data, parent):
    """Export time series data to an Excel file with simulated and measured data in 
    separate sheets, inlcuding line chart.

    Args:
        plot_data (list): List of datasets containing labels, y-values, and data type
        (simulated/measured) 
        parent: Parent widget for the QFileDialog
    """

    # Open file save dialog for Excel file
    options = QFileDialog.Options()
    file_path, _ = QFileDialog.getSaveFileName(
        parent,
        "Save Time Series to Excel",
        "",
        "Excel Files (*.xlsx);;All Files (*)",
        options=options
    )
    if not file_path:
        return

    # Initialize dictionaries to store simulated and measured data
    simulated_dict = defaultdict(list)
    measured_dict = defaultdict(dict)
    max_len = 0

    # Separate data into simulated and measured dictionaries
    for dataset in plot_data:
        label = dataset.get('label', 'No label')
        y_vals = dataset.get('y', [])
        data_type = dataset.get('type', 'simulated')
        if data_type == 'simulated':
            simulated_dict[label] = y_vals
            max_len = max(max_len, len(y_vals))
        elif data_type == 'measured':
            x_vals = dataset.get('x_calendar', [])
            for x, y in zip(x_vals, y_vals):
                measured_dict[x][f"{label} (Measured)"] = y

    # Create DataFrame for simulated data (indexed by Day)
    df_sim = pd.DataFrame({'Day': range(1, max_len + 1)})
    for label, y_vals in simulated_dict.items():
        padded = y_vals + [None] * (max_len - len(y_vals))
        df_sim[f"{label} (Simulated)"] = padded

    # Create DataFrame for measured data (indexed by Date)
    df_meas = pd.DataFrame.from_dict(measured_dict, orient='index')
    df_meas.index.name = 'Date'
    df_meas.reset_index(inplace=True)
    df_meas.sort_values(by='Date', inplace=True)

    # Write Excel with formatting and chart
    with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
        workbook = writer.book
        header_format = workbook.add_format({
            'bold': True, 'bg_color': '#D3D3D3',
            'border': 1, 'align': 'center'
        })
        cell_format = workbook.add_format({'border': 1})

        # Write Simulated sheet
        df_sim.to_excel(writer, sheet_name='Simulated', index=False, startrow=1)
        ws_sim = writer.sheets['Simulated']
        for col_num, col in enumerate(df_sim.columns):
            ws_sim.write(0, col_num, col, header_format)
        for row_num, row in df_sim.iterrows():
            for col_num, val in enumerate(row):
                ws_sim.write(row_num + 1, col_num, val if pd.notna(val) else '', cell_format)

        # Write Measured data sheet
        df_meas.to_excel(writer, sheet_name='Measured', index=False, startrow=1)
        ws_meas = writer.sheets['Measured']
        for col_num, col in enumerate(df_meas.columns):
            ws_meas.write(0, col_num, col, header_format)
        for row_num, row in df_meas.iterrows():
            for col_num, val in enumerate(row):
                ws_meas.write(row_num + 1, col_num, val if pd.notna(val) else '', cell_format)

        # Create line chart for simulated data
        chart_sheet = workbook.add_worksheet('Chart')
        chart = workbook.add_chart({'type': 'line'})
        added_series = False
        for i, col in enumerate(df_sim.columns[1:], 1):  # Skip "Day"
            col_letter = chr(65 + i)
            if df_sim[col].count() < 2:
                continue
            chart.add_series({
                'name':       col,
                'categories': f"Simulated!$A$2:$A${len(df_sim)+1}",
                'values':     f"Simulated!${col_letter}$2:${col_letter}${len(df_sim)+1}",
                'line': {'width': 1.5}
            })
            added_series = True

        if added_series:
            chart.set_title({'name': 'Simulated Time Series'})
            chart.set_x_axis({'name': 'Day'})
            chart.set_y_axis({'name': 'Value'})
            chart.set_legend({'position': 'top'})
            chart_sheet.insert_chart('B2', chart, {'x_scale': 2, 'y_scale': 1.5})
        else:
            chart_sheet.write('A1', 'No valid simulated series to display.')


def export_data_to_txt_scatter(plot_data, parent):
    """Export scatter plot data to a TXT file with aligned columns for X and Y values.
    
    Args:
        plot_data (list): List of tuples containing (x_values, y_values, label).
        parent: Parent widget for the QFileDialog.
    """
    # Open file save dialog for the TXT file
    options = QFileDialog.Options()
    file_path, _ = QFileDialog.getSaveFileName(parent, "Save Scatter Plot Data to TXT", "", "Text Files (*.txt);;All Files (*)", options=options)
    if file_path:
        # Create DataFrame with aligned data
        max_len = max(len(x) for x, _, _ in plot_data)
        df = pd.DataFrame({'Day': range(1, max_len + 1)})
    
        # Add X and Y values for each dataset
        for x_values, y_values, label in plot_data:
            # Fill missing values with None to ensure equal length
            x_values = list(x_values) + [None] * (max_len - len(x_values))
            y_values = list(y_values) + [None] * (max_len - len(y_values))
            df[f'{label} X'] = x_values
            df[f'{label} Y'] = y_values

        # Align column widths
        column_widths = {col: max(len(col), df[col].astype(str).map(len).max()) for col in df.columns}

        # Write to TXT file with aligned columns
        with open(file_path, 'w') as f:
            header = '\t'.join(col.ljust(column_widths[col]) for col in df.columns)
            f.write(header + '\n')
            for _, row in df.iterrows():
                line = '\t'.join(
                    str(item).ljust(column_widths[col]) if item is not None else ' ' * column_widths[col]
                    for col, item in zip(df.columns, row)
                )
                f.write(line + '\n')
                
def export_data_to_excel_scatter(plot_data, parent):
    """Export scatter plot data to an Excel file with a combined scatter chart.
    
    Args:
        plot_data (list): List of tuples containing (x_values, y_values, label).
        parent: Parent Widget for QFileDialog.
    """
    # Import required for column letter conversion
    from string import ascii_uppercase

    # Open file save dialog for Excel file 
    options = QFileDialog.Options()
    file_path, _ = QFileDialog.getSaveFileName(
        parent,
        "Save Scatter Plot Data & Graph to Excel",
        "",
        "Excel Files (*.xlsx);;All Files (*)",
        options=options
    )
    if file_path:
        # Write to Excel formatting chart 
        with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
            workbook = writer.book
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#D3D3D3',
                'border': 1,
                'align': 'center'
            })
            cell_format = workbook.add_format({'border': 1})

            # Get max data length
            max_length = max(len(x_values) for x_values, _, _ in plot_data)

            # Create data table
            df = pd.DataFrame({'Index': range(1, max_length + 1)})
            for x_values, y_values, label in plot_data:
                x_series = pd.Series(x_values).reindex(range(max_length))
                y_series = pd.Series(y_values).reindex(range(max_length))
                df[f'{label} X'] = x_series
                df[f'{label} Y'] = y_series

            # Write to Excel
            df.to_excel(writer, sheet_name='Data', startrow=1, index=False)

            worksheet = writer.sheets['Data']

            # Header formatting
            for col_num, value in enumerate(df.columns):
                worksheet.write(0, col_num, value, header_format)

            # Cell formatting
            for row_num, row in df.iterrows():
                for col_num, value in enumerate(row):
                    worksheet.write(row_num + 1, col_num, value if pd.notna(value) else '', cell_format)

            # Column width auto-adjust
            for col_num, col in enumerate(df.columns):
                max_len = max(len(str(col)), df[col].astype(str).map(len).max())
                worksheet.set_column(col_num, col_num, max_len + 2)

            # Create single combined chart
            chart_sheet = workbook.add_worksheet('Charts')
            chart = workbook.add_chart({'type': 'scatter'})

            for idx, (_, _, label) in enumerate(plot_data):
                x_col_idx = 1 + 2 * idx  # X columns: 1, 3, 5...
                y_col_idx = x_col_idx + 1

                # Convert to Excel letters (supports >26 cols)
                def col_letter(idx):
                    letters = ''
                    while idx >= 0:
                        letters = chr(65 + (idx % 26)) + letters
                        idx = idx // 26 - 1
                    return letters

                x_col_letter = col_letter(x_col_idx)
                y_col_letter = col_letter(y_col_idx)

                chart.add_series({
                    'name': label,
                    'categories': f"'Data'!${x_col_letter}$2:${x_col_letter}${max_length + 1}",
                    'values': f"'Data'!${y_col_letter}$2:${y_col_letter}${max_length + 1}",
                    'marker': {'type': 'circle', 'size': 6}
                })

            chart.set_title({'name': 'Scatter Plot - All Runs'})
            chart.set_x_axis({'name': 'X Variable'})
            chart.set_y_axis({'name': 'Y Variable'})
            chart.set_legend({'position': 'top'})

            chart_sheet.insert_chart('B2', chart, {'x_scale': 2, 'y_scale': 1.5})

def export_data_to_txt_evaluate(plot_data, parent):
    """Export evaluation data (simulated vs measured) to a TXT file
    
    Args:
        plot_data (list): List of datasets containing labels, x-values (simulated), and y-values (measured).
        parent: Parent widget for the QFileDialog.
        """
    # Open file save dialog for TXT file
    options = QFileDialog.Options()
    file_path, _ = QFileDialog.getSaveFileName(parent, "Save Evaluate Data to TXT", "", "Text Files (*.txt);;All Files (*)", options=options)
    if file_path:
        # Write evaluation data TXT file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("Evaluate Data\n")
            f.write("Index\tSimulated\tMeasured\tVariable\n")
            for data in plot_data:
                label = data.get('label', 'No label')
                x_values = data.get('x', [])
                y_values = data.get('y', [])
                if not x_values or not y_values:
                    continue
                f.write(f"{label}\n")
                f.write("Index\tSimulated\tMeasured\n")
                for x, y in zip(x_values, y_values):
                    f.write(f"{x}\t{x if x is not None else ''}\t{y if y is not None else ''}\n")
                f.write("\n")

def export_data_to_excel_evaluate(plot_data, parent):
    """Export evaluation data to an Excel file with scatter chart comparing simulated vs measured data.
    
    Args:
        plot_data (list): List of datasets containing labels, x-values (simulated), and y-values (measured).
        parent: Parent widget for the QFileDialog
    """
    # Open file save dialog for Excel file
    options = QFileDialog.Options()
    file_path, _ = QFileDialog.getSaveFileName(parent, "Save Evaluate Data & Graph to Excel", "", "Excel Files (*.xlsx);;All Files (*)", options=options)
    if file_path:
        # Write Excel file with formatting and chart
        with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
            workbook = writer.book
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#D3D3D3',
                'border': 1,
                'align': 'center'
            })
            cell_format = workbook.add_format({'border': 1})

            # Prepare data
            max_length = max(len(data.get('x', [])) for data in plot_data) if plot_data else 0
            if max_length == 0:
                raise ValueError("No data to export.")

            df = pd.DataFrame({'Index': range(1, max_length + 1)})
            for data in plot_data:
                label = data.get('label', 'No label')
                x_vals = data.get('x', [None] * max_length)
                y_vals = data.get('y', [None] * max_length)
                df[f'{label} Simulated'] = x_vals
                df[f'{label} Measured'] = y_vals

            # Write DataFrame to Excel
            df.to_excel(writer, sheet_name='Data', startrow=1, index=False)
            worksheet = writer.sheets['Data']

            # Headers
            for col_num, value in enumerate(df.columns):
                worksheet.write(0, col_num, value, header_format)

            # Data
            for row_num, row in df.iterrows():
                for col_num, value in enumerate(row):
                    worksheet.write(row_num + 1, col_num, value if pd.notna(value) else '', cell_format)

            # Column widths
            for col_num, col in enumerate(df.columns):
                max_len = max(len(str(col)), df[col].astype(str).map(len).max())
                worksheet.set_column(col_num, col_num, max_len + 2)

            # Chart
            chart_sheet = workbook.add_worksheet('Charts')
            chart = workbook.add_chart({'type': 'scatter'})

            for idx, data in enumerate(plot_data):
                label = data.get('label', 'No label')
                x_col_idx = 2 * idx + 1  # Simulated columns: 1, 3, 5...
                y_col_idx = x_col_idx + 1  # Measured columns: 2, 4, 6...

                def col_letter(idx):
                    letters = ''
                    while idx >= 0:
                        letters = chr(65 + (idx % 26)) + letters
                        idx = idx // 26 - 1
                    return letters

                x_col_letter = col_letter(x_col_idx)
                y_col_letter = col_letter(y_col_idx)

                chart.add_series({
                    'name': label,
                    'categories': f"'Data'!${x_col_letter}$2:${x_col_letter}${max_length + 1}",
                    'values': f"'Data'!${y_col_letter}$2:${y_col_letter}${max_length + 1}",
                    'marker': {'type': 'circle', 'size': 6}
                })

            chart.set_title({'name': 'Evaluate Data (Simulated vs Measured)'})
            chart.set_x_axis({'name': 'Simulated'})
            chart.set_y_axis({'name': 'Measured'})
            chart.set_legend({'position': 'top'})
            chart_sheet.insert_chart('B2', chart, {'x_scale': 2, 'y_scale': 1.5})

def export_tfile_to_txt(plot_data, parent, use_calendar_mode=True):
    """Export T file data to a TXT file, using either calendar dates or DAP (days after planting).
    
    Args:
        plot_data (list): List of datasets containing labels, x-values, and y-values.
        parent: Parent widget for the QFileDialog
        use_calendar_mode (bool): True to use calendar dates, False to use DAP.
    """
    # Open file save dialog for TXT file
    options = QFileDialog.Options()
    file_path, _ = QFileDialog.getSaveFileName(parent, "Save T File Data to TXT", "", "Text Files (*.txt);;All Files (*)", options=options)
    if not file_path:
        return

    # Determine x-axis key and label based on mode
    x_key = 'x_calendar' if use_calendar_mode else 'x_dap'
    x_label = 'Date' if use_calendar_mode else 'DAP'

    # Build dictionary for DataFrame
    data_dict = defaultdict(dict)
    for dataset in plot_data:
        label = dataset['label']
        x_vals = dataset.get(x_key)
        y_vals = dataset.get('y')
        for x, y in zip(x_vals, y_vals):
            data_dict[x][label] = y

    # Create and sort DataFrame 
    df = pd.DataFrame.from_dict(data_dict, orient='index')
    df.index.name = x_label
    df.sort_index(inplace=True)
    df.reset_index(inplace=True)

    # Calculate column widths for alignment 
    column_widths = {col: max(len(str(col)), df[col].astype(str).map(len).max()) for col in df.columns}

    # Write to TXT file with aligned columns 
    with open(file_path, 'w') as f:
        header = '\t'.join(col.ljust(column_widths[col]) for col in df.columns)
        f.write(header + '\n')
        for _, row in df.iterrows():
            line = '\t'.join(str(row[col]).ljust(column_widths[col]) if pd.notnull(row[col]) else ' ' * column_widths[col] for col in df.columns)
            f.write(line + '\n')


def export_tfile_to_excel(plot_data, parent, use_calendar_mode=True):
    """Export T file data to an Excel file with a line chart, using either calendar dates or DAP
    
    Args:
        plot_data (list): List of datasets containing labels, x-values, and y-values.
        parent: Parent widget for the QFileDialog.
        use_calendar_mode (bool): True to use calendar dates, False to use DAP.
        """
    # Open save dialog for Excel file 
    options = QFileDialog.Options()
    file_path, _ = QFileDialog.getSaveFileName(parent, "Save T File Data to Excel", "", "Excel Files (*.xlsx);;All Files (*)", options=options)
    if not file_path:
        return

    # Determine x-axis key and label based on mode
    x_key = 'x_calendar' if use_calendar_mode else 'x_dap'
    x_label = 'Date' if use_calendar_mode else 'DAP'

    # Build dictionary for DataFrame 
    data_dict = defaultdict(dict)
    for dataset in plot_data:
        label = dataset['label']
        x_vals = dataset.get(x_key)
        y_vals = dataset.get('y')
        for x, y in zip(x_vals, y_vals):
            data_dict[x][label] = y

    # Create and Sort DataFrame
    df = pd.DataFrame.from_dict(data_dict, orient='index')
    df.index.name = x_label
    df.sort_index(inplace=True)
    df.reset_index(inplace=True)

    # Write to Excel with formatting and chart
    with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Data', index=False, startrow=1)

        workbook = writer.book
        worksheet = writer.sheets['Data']

        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D3D3D3',
            'border': 1,
            'align': 'center'
        })
        cell_format = workbook.add_format({'border': 1})

        # Write headers 
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)

        # Write data
        for row_num, row in df.iterrows():
            for col_num, val in enumerate(row):
                worksheet.write(row_num + 1, col_num, val if pd.notnull(val) else '', cell_format)

        # Auto-adjust column widths
        for col_num, col in enumerate(df.columns):
            max_length = max(len(str(col)), df[col].astype(str).map(len).max())
            worksheet.set_column(col_num, col_num, max_length + 2)

        # Create a line chart
        chart_sheet = workbook.add_worksheet('Charts')
        chart = workbook.add_chart({'type': 'line'})

        for i, col in enumerate(df.columns[1:], 1):
            col_letter = chr(65 + i)
            chart.add_series({
                'name':       f'=Data!${col_letter}$1',
                'categories': f'=Data!$A$2:$A${len(df)+1}',
                'values':     f'=Data!${col_letter}$2:${col_letter}${len(df)+1}',
                'line': {'width': 1.5}
            })

        chart.set_title({'name': 'T File Data'})
        chart.set_x_axis({'name': x_label})
        chart.set_y_axis({'name': 'Value'})
        chart.set_legend({'position': 'top'})
        chart_sheet.insert_chart('B2', chart, {'x_scale': 2, 'y_scale': 1.5})
