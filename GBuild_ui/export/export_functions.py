# C:\Users\User\Documents\Projetos\interface_Gbuild_refatorada\export\export_functions.py
import pandas as pd
from PyQt5.QtWidgets import QFileDialog
from collections import defaultdict

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
            workbook = writer.book
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#D3D3D3',
                'border': 1,
                'align': 'center'
            })
            cell_format = workbook.add_format({'border': 1})

            # Consolidate all scatter data into a single Data sheet
            max_length = max(len(x_values) for x_values, _, _ in plot_data)
            df = pd.DataFrame(index=range(1, max_length + 1))
            for idx, (x_values, y_values, label) in enumerate(plot_data):
                x_col = f"{label} X"
                y_col = f"{label} Y"
                df[x_col] = pd.Series(x_values).reindex(range(max_length))
                df[y_col] = pd.Series(y_values).reindex(range(max_length))

            df.to_excel(writer, sheet_name='Data', startrow=1)

            worksheet = writer.sheets['Data']
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num + 1, value, header_format)
            worksheet.write(0, 0, 'Index', header_format)

            # Write data with formatting
            for row_num, row in df.iterrows():
                worksheet.write(row_num + 1, 0, row.name, cell_format)  # Index
                for col_num, value in enumerate(row[1:], 1):  # Skip index column
                    worksheet.write(row_num + 1, col_num, value if value is not None else '', cell_format)

            for col_num, col in enumerate(df.columns, 1):
                max_length = max(len(str(col)), df[col].astype(str).map(len).max())
                worksheet.set_column(col_num, col_num, max_length + 2)
            worksheet.set_column(0, 0, 10)

            chart_sheet = workbook.add_worksheet('Charts')

            for idx, (_, _, label) in enumerate(plot_data):
                chart = workbook.add_chart({'type': 'scatter'})
                x_col_idx = 2 * idx + 1  # X column (1, 3, 5, ...)
                y_col_idx = 2 * idx + 2  # Y column (2, 4, 6, ...)

                chart.add_series({
                    'name': label,
                    'categories': f"'Data'!${chr(65 + x_col_idx)}$2:${chr(65 + x_col_idx)}${max_length + 1}",
                    'values': f"'Data'!${chr(65 + y_col_idx)}$2:${chr(65 + y_col_idx)}${max_length + 1}",
                    'marker': {'type': 'circle', 'size': 6, 'fill': {'color': 'blue'}}
                })

                chart.set_title({'name': f'Scatter Plot - {label}'})
                chart.set_x_axis({'name': 'X Variable', 'major_gridlines': {'visible': True}})
                chart.set_y_axis({'name': 'Y Variable', 'major_gridlines': {'visible': True}})
                chart.set_legend({'position': 'top'})
                chart_sheet.insert_chart(f'B{2 + 15 * idx}', chart, {'x_scale': 1.5, 'y_scale': 1.5})

def export_data_to_txt_evaluate(plot_data, parent):
    options = QFileDialog.Options()
    file_path, _ = QFileDialog.getSaveFileName(parent, "Save Evaluate Data to TXT", "", "Text Files (*.txt);;All Files (*)", options=options)
    if file_path:
        with open(file_path, 'w') as f:
            f.write("Evaluate Data\n")
            f.write("Index\tValue\tVariable\n")
            for data in plot_data:
                label = data.get('label', 'No label')
                x_values = data.get('x', [])
                y_values = data.get('y', [])
                f.write(f"{label}\n")
                f.write("Index\tValue\n")
                for x, y in zip(x_values, y_values):
                    f.write(f"{x}\t{y}\n")
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

            df = pd.DataFrame()
            for data in plot_data:
                label = data.get('label', 'No label')
                values = data.get('y', [])
                df[label] = values

            df.index = range(1, len(df) + 1)
            df.index.name = 'Index'
            df.to_excel(writer, sheet_name='Data', startrow=1)

            worksheet = writer.sheets['Data']
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num + 1, value, header_format)
            worksheet.write(0, 0, 'Index', header_format)

            # Write data with formatting
            for row_num, row in df.iterrows():
                worksheet.write(row_num + 1, 0, row.name, cell_format)  # Index
                for col_num, value in enumerate(row[1:], 1):  # Skip index column
                    worksheet.write(row_num + 1, col_num, value if value is not None else '', cell_format)

            worksheet.set_column(0, 0, 10)
            for col_num, col in enumerate(df.columns, 1):
                max_length = max(len(str(col)), df[col].astype(str).map(len).max())
                worksheet.set_column(col_num, col_num, max_length + 2)

            chart_sheet = workbook.add_worksheet('Charts')
            chart = workbook.add_chart({'type': 'column'})

            for i, col in enumerate(df.columns, 1):
                chart.add_series({
                    'name': col,
                    'categories': f'Data!$A$2:$A${len(df) + 1}',
                    'values': f'Data!${chr(65 + i)}$2:${chr(65 + i)}${len(df) + 1}',
                    'fill': {'color': 'blue'}
                })

            chart.set_title({'name': 'Evaluate Data'})
            chart.set_x_axis({'name': 'Index', 'major_gridlines': {'visible': True}})
            chart.set_y_axis({'name': 'Value', 'major_gridlines': {'visible': True}})
            chart.set_legend({'position': 'top'})
            chart_sheet.insert_chart('B2', chart, {'x_scale': 2, 'y_scale': 1.5})