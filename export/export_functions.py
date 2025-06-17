# C:\Users\User\Documents\Projetos\interface_Gbuild_refatorada\export\export_functions.py
import pandas as pd
from PyQt5.QtWidgets import QFileDialog
from collections import defaultdict
from xlsxwriter.utility import xl_col_to_name

def export_data_to_txt_time_series(plot_data, parent):
    options = QFileDialog.Options()
    file_path, _ = QFileDialog.getSaveFileName(parent, "Save Time Series to TXT", "", "Text Files (*.txt);;All Files (*)", options=options)
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

def export_data_to_excel_time_series(plot_data, parent):
    options = QFileDialog.Options()
    file_path, _ = QFileDialog.getSaveFileName(parent, "Save Time Series to Excel", "", "Excel Files (*.xlsx);;All Files (*)", options=options)
    if file_path:
        with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
            df = pd.DataFrame()
            for dataset in plot_data:
                label = dataset.get('label', 'No label')
                values = dataset.get('y', [])
                df[label] = values

            df.index = range(1, len(df) + 1)
            df.index.name = 'Day'
            df.to_excel(writer, sheet_name='Data', startrow=1)

            workbook = writer.book
            worksheet = writer.sheets['Data']

            # Formatting
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#D3D3D3',
                'border': 1,
                'align': 'center'
            })
            cell_format = workbook.add_format({'border': 1})

            # Write headers
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num + 1, value, header_format)
            worksheet.write(0, 0, 'Day', header_format)

            # Write data with formatting
            for row_num, row in df.iterrows():
                worksheet.write(row_num + 1, 0, row.name, cell_format)  # Day index
                for col_num, value in enumerate(row[1:], 1):  # Skip index column
                    worksheet.write(row_num + 1, col_num, value if value is not None else '', cell_format)

            # Adjust column widths
            worksheet.set_column(0, 0, 10)  # Day column
            for col_num, col in enumerate(df.columns, 1):
                max_length = max(len(str(col)), df[col].astype(str).map(len).max())
                worksheet.set_column(col_num, col_num, max_length + 2)

            # Create chart sheet
            chart_sheet = workbook.add_worksheet('Charts')
            chart = workbook.add_chart({'type': 'line'})

            for i, col in enumerate(df.columns, 1):
                chart.add_series({
                    'name': col,
                    'categories': f'Data!$A$2:$A${len(df) + 1}',
                    'values': f'Data!${chr(65 + i)}$2:${chr(65 + i)}${len(df) + 1}',
                    'line': {'width': 1.5}
                })

            chart.set_title({'name': 'Time Series Data'})
            chart.set_x_axis({'name': 'Day', 'major_gridlines': {'visible': True}})
            chart.set_y_axis({'name': 'Value', 'major_gridlines': {'visible': True}})
            chart.set_legend({'position': 'top'})
            chart_sheet.insert_chart('B2', chart, {'x_scale': 2, 'y_scale': 1.5})

def export_data_to_txt_scatter(plot_data, parent):
    options = QFileDialog.Options()
    file_path, _ = QFileDialog.getSaveFileName(parent, "Save Scatter Plot Data to TXT", "", "Text Files (*.txt);;All Files (*)", options=options)
    if file_path:
        max_len = max(len(x) for x, _, _ in plot_data)
        df = pd.DataFrame({'Day': range(1, max_len + 1)})

        for x_values, y_values, label in plot_data:
            # Fill missing values with None to ensure equal length
            x_values = list(x_values) + [None] * (max_len - len(x_values))
            y_values = list(y_values) + [None] * (max_len - len(y_values))
            df[f'{label} X'] = x_values
            df[f'{label} Y'] = y_values

        # Align column widths
        column_widths = {col: max(len(col), df[col].astype(str).map(len).max()) for col in df.columns}

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
    from string import ascii_uppercase

    options = QFileDialog.Options()
    file_path, _ = QFileDialog.getSaveFileName(
        parent,
        "Save Scatter Plot Data & Graph to Excel",
        "",
        "Excel Files (*.xlsx);;All Files (*)",
        options=options
    )
    if file_path:
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
    options = QFileDialog.Options()
    file_path, _ = QFileDialog.getSaveFileName(parent, "Save Evaluate Data to TXT", "", "Text Files (*.txt);;All Files (*)", options=options)
    if file_path:
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
    options = QFileDialog.Options()
    file_path, _ = QFileDialog.getSaveFileName(parent, "Save Evaluate Data & Graph to Excel", "", "Excel Files (*.xlsx);;All Files (*)", options=options)
    if file_path:
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
    options = QFileDialog.Options()
    file_path, _ = QFileDialog.getSaveFileName(parent, "Save T File Data to TXT", "", "Text Files (*.txt);;All Files (*)", options=options)
    if not file_path:
        return

    x_key = 'x_calendar' if use_calendar_mode else 'x_dap'
    x_label = 'Date' if use_calendar_mode else 'DAP'

    data_dict = defaultdict(dict)

    for dataset in plot_data:
        label = dataset['label']
        x_vals = dataset.get(x_key)
        y_vals = dataset.get('y')

        for x, y in zip(x_vals, y_vals):
            data_dict[x][label] = y

    df = pd.DataFrame.from_dict(data_dict, orient='index')
    df.index.name = x_label
    df.sort_index(inplace=True)
    df.reset_index(inplace=True)

    column_widths = {col: max(len(str(col)), df[col].astype(str).map(len).max()) for col in df.columns}

    with open(file_path, 'w') as f:
        header = '\t'.join(col.ljust(column_widths[col]) for col in df.columns)
        f.write(header + '\n')
        for _, row in df.iterrows():
            line = '\t'.join(str(row[col]).ljust(column_widths[col]) if pd.notnull(row[col]) else ' ' * column_widths[col] for col in df.columns)
            f.write(line + '\n')

import pandas as pd
from PyQt5.QtWidgets import QFileDialog

def export_tfile_to_excel(plot_data, parent, use_calendar_mode=True):
    options = QFileDialog.Options()
    file_path, _ = QFileDialog.getSaveFileName(parent, "Save T File Data to Excel", "", "Excel Files (*.xlsx);;All Files (*)", options=options)
    if not file_path:
        return

    x_key = 'x_calendar' if use_calendar_mode else 'x_dap'
    x_label = 'Date' if use_calendar_mode else 'DAP'

    data_dict = defaultdict(dict)
    for dataset in plot_data:
        label = dataset['label']
        x_vals = dataset.get(x_key)
        y_vals = dataset.get('y')
        for x, y in zip(x_vals, y_vals):
            data_dict[x][label] = y

    df = pd.DataFrame.from_dict(data_dict, orient='index')
    df.index.name = x_label
    df.sort_index(inplace=True)
    df.reset_index(inplace=True)

    with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Data', index=False, startrow=1)

        workbook = writer.book
        worksheet = writer.sheets['Data']

        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D3D3D3',
            'border': 1,
            'align': 'center'
        })
        cell_format = workbook.add_format({'border': 1})

        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)

        for row_num, row in df.iterrows():
            for col_num, val in enumerate(row):
                worksheet.write(row_num + 1, col_num, val if pd.notnull(val) else '', cell_format)

        for col_num, col in enumerate(df.columns):
            max_length = max(len(str(col)), df[col].astype(str).map(len).max())
            worksheet.set_column(col_num, col_num, max_length + 2)

        # Gráfico
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
