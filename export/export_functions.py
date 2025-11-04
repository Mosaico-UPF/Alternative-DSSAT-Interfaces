from datetime import date, datetime, timedelta
import pandas as pd
from PyQt5.QtWidgets import QFileDialog
from collections import defaultdict
from xlsxwriter.utility import xl_col_to_name

from utils.stats_calculator import calculate_statistics

def export_data_to_txt_time_series(plot_data, parent):
    """ Export time series data to a TXT file with simulated and measured data aligned in a single table

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
    
    # Initialize dictionary to store all data (simulated and measured in one table)
    data_dict = defaultdict(dict)
    max_len = 0
    dates = []

    # Collect all data and determine if dates are available
    has_dates = any('x_calendar' in dataset for dataset in plot_data)
    if has_dates:
        dates = next(dataset['x_calendar'] for dataset in plot_data if 'x_calendar' in dataset)
    else:
        dates = list(range(1, max(len(dataset['y']) for dataset in plot_data) + 1))

    for dataset in plot_data:
        label = dataset.get('label', 'No label')
        y_vals = dataset.get('y', [])
        data_type = dataset.get('type', 'simulated')
        suffix = ' (measured)' if data_type == 'measured' else ''
        for i, y in enumerate(y_vals):
            data_dict[i][f"{label}{suffix}"] = y
        max_len = max(max_len, len(y_vals))

    # Build DataFrame
    df = pd.DataFrame.from_dict(data_dict, orient='index')
    df.sort_index(inplace=True)
    df.insert(0, 'Date', dates[:max_len])
    df.fillna('', inplace=True)

    # Calculate column widths
    col_widths = {col: max(len(str(col)), df[col].astype(str).map(len).max() + 2) for col in df.columns}

    # Write to TXT with aligned columns using spaces
    with open(file_path, 'w', encoding='utf-8') as f:
        header = ' '.join(str(col).ljust(col_widths[col]) for col in df.columns)
        f.write(header + '\n')
        for _, row in df.iterrows():
            line = ' '.join(str(row[col]).ljust(col_widths[col]) for col in df.columns)
            f.write(line + '\n')

def export_data_to_excel_time_series(plot_data, parent):
    """Export time series data to an Excel file with all data in one sheet and a chart.

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

    # Initialize dictionary to store all data
    data_dict = defaultdict(dict)
    max_len = 0
    dates = []

    # Collect dates if available
    has_dates = any('x_calendar' in dataset for dataset in plot_data)
    if has_dates:
        dates = next(dataset['x_calendar'] for dataset in plot_data if 'x_calendar' in dataset)
    else:
        dates = list(range(1, max(len(dataset['y']) for dataset in plot_data) + 1))

    for dataset in plot_data:
        label = dataset.get('label', 'No label')
        y_vals = dataset.get('y', [])
        data_type = dataset.get('type', 'simulated')
        suffix = ' (measured)' if data_type == 'measured' else ''
        for i, y in enumerate(y_vals):
            data_dict[i][f"{label}{suffix}"] = y
        max_len = max(max_len, len(y_vals))

    # Build DataFrame
    df = pd.DataFrame.from_dict(data_dict, orient='index')
    df.sort_index(inplace=True)
    df.insert(0, 'Date', dates[:max_len])
    df.fillna('', inplace=True)

    # Write to Excel
    with pd.ExcelWriter(file_path, engine='xlsxwriter', date_format='YYYY-MM-DD' if has_dates else None) as writer:
        workbook = writer.book
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'border': 1, 'align': 'center'})
        cell_format = workbook.add_format({'border': 1})

        df.to_excel(writer, sheet_name='Data', index=False, startrow=0)

        ws_data = writer.sheets['Data']
        for col_num, col in enumerate(df.columns):
            ws_data.write(0, col_num, col, header_format)
            max_len = max(len(str(col)), df[col].astype(str).map(len).max())
            ws_data.set_column(col_num, col_num, max_len + 2)
        for row_num, row in df.iterrows():
            for col_num, val in enumerate(row):
                ws_data.write(row_num + 1, col_num, val if pd.notna(val) else '', cell_format)

        # Chart sheet
        chart_sheet = workbook.add_worksheet('Charts')
        chart = workbook.add_chart({'type': 'line'})
        for i, col in enumerate(df.columns[1:], 1):
            col_letter = xl_col_to_name(i)
            chart.add_series({
                'name': col,
                'categories': f"Data!$A$2:$A${len(df) + 1}",
                'values': f"Data!${col_letter}$2:${col_letter}${len(df) + 1}",
                'line': {'width': 1.5}
            })
        chart.set_title({'name': 'Time Series'})
        chart.set_x_axis({'name': 'Date'})
        chart.set_y_axis({'name': 'Value'})
        chart.set_legend({'position': 'top'})
        chart_sheet.insert_chart('B2', chart, {'x_scale': 2, 'y_scale': 1.5})

def export_data_to_txt_scatter(parent):
    """Export scatter plot data to a TXT file with aligned columns
    
    Args:
        parent: GraphWindow instance containing plot_data, sim_vs_meas
    """
    plot_data = parent.plot_data
    sim_vs_meas = parent.sim_vs_meas

    options = QFileDialog.Options()
    file_path, _ = QFileDialog.getSaveFileName(parent, "Save Scatter Plot Data to TXT", "", "Text Files (*.txt);;All Files (*)", options=options)
    if not file_path:
        return

    df = pd.DataFrame()
    max_len = max(max(len(d['x']), len(d['y'])) for d in plot_data)
    df['Day'] = range(1, max_len + 1)

    for dataset in plot_data:
        label = dataset['label']
        x_padded = dataset['x'] + [None] * (max_len - len(dataset['x']))
        y_padded = dataset['y'] + [None] * (max_len - len(dataset['y']))

        if sim_vs_meas:
            df[f"{label} Simulated"] = x_padded
            df[f"{label} Measured"] = y_padded
        else:
            parts = label.split(' vs ')
            if len(parts) == 2:
                x_cde = parts[0]
                y_cde_run = parts[1]
                y_cde = y_cde_run.split(' (')[0]
                run = y_cde_run.split(' (')[1][:-1]
                df[f"{x_cde} {run}"] = x_padded
                df[f"{y_cde} {run}"] = y_padded

    col_widths = {col: max(len(str(col)), df[col].astype(str).map(len).max() + 2) for col in df.columns if df[col].notna().any()}

    with open(file_path, 'w') as f:
        header = ' '.join(str(col).ljust(col_widths.get(col, 0)) for col in df.columns)
        f.write(header + '\n')
        for _, row in df.iterrows():
            line = ' '.join(str(row[col]).ljust(col_widths.get(col, 0)) if pd.notna(row[col]) else ' ' * col_widths.get(col, 0) for col in df.columns)
            f.write(line + '\n')

def export_data_to_excel_scatter(parent):
    """Export scatter plot data to an Excel file with chart
    
    Args:
        parent: GraphWindow instance.
    """
    plot_data = parent.plot_data
    sim_vs_meas = parent.sim_vs_meas

    options = QFileDialog.Options()
    file_path, _ = QFileDialog.getSaveFileName(parent, "Save Scatter Plot Data & Graph to Excel", "", "Excel Files (*.xlsx);;All Files (*)", options=options)
    if not file_path:
        return

    df = pd.DataFrame()
    max_len = max(max(len(d['x']), len(d['y'])) for d in plot_data)
    df['Day'] = range(1, max_len + 1)

    for dataset in plot_data:
        label = dataset['label']
        x_padded = dataset['x'] + [None] * (max_len - len(dataset['x']))
        y_padded = dataset['y'] + [None] * (max_len - len(dataset['y']))

        if sim_vs_meas:
            df[f"{label} Simulated"] = x_padded
            df[f"{label} Measured"] = y_padded
        else:
            parts = label.split(' vs ')
            if len(parts) == 2:
                x_cde = parts[0]
                y_cde_run = parts[1]
                y_cde = y_cde_run.split(' (')[0]
                run = y_cde_run.split(' (')[1][:-1]
                df[f"{x_cde} {run}"] = x_padded
                df[f"{y_cde} {run}"] = y_padded

    with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
        workbook = writer.book
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'border': 1, 'align': 'center'})
        cell_format = workbook.add_format({'border': 1})

        df.to_excel(writer, sheet_name='Data', index=False, startrow=0)
        ws_data = writer.sheets['Data']
        for col_num, col in enumerate(df.columns):
            ws_data.write(0, col_num, col, header_format)
        for row_num, row in df.iterrows():
            for col_num, val in enumerate(row):
                ws_data.write(row_num + 1, col_num, val if pd.notna(val) else '', cell_format)
        for col_num, col in enumerate(df.columns):
            max_len_col = max(len(str(col)), df[col].astype(str).map(len).max())
            ws_data.set_column(col_num, col_num, max_len_col + 2)

        # Chart
        chart_sheet = workbook.add_worksheet('Charts')
        chart = workbook.add_chart({'type': 'scatter'})
        col_indices = {col: idx for idx, col in enumerate(df.columns[1:])}
        for dataset in plot_data:
            label = dataset['label']
            if sim_vs_meas:
                x_col = f"{label} Simulated"
                y_col = f"{label} Measured"
            else:
                parts = label.split(' vs ')
                if len(parts) != 2:
                    continue
                x_cde = parts[0]
                y_cde_run = parts[1]
                y_cde = y_cde_run.split(' (')[0]
                run = y_cde_run.split(' (')[1][:-1]
                x_col = f"{x_cde} {run}"
                y_col = f"{y_cde} {run}"
            if x_col in col_indices and y_col in col_indices:
                x_letter = xl_col_to_name(col_indices[x_col] + 1)
                y_letter = xl_col_to_name(col_indices[y_col] + 1)
                chart.add_series({
                    'name': label,
                    'categories': f"Data!${x_letter}$2:${x_letter}${max_len + 1}",
                    'values': f"Data!${y_letter}$2:${y_letter}${max_len + 1}",
                    'marker': {'type': 'circle', 'size': 6}
                })
        chart.set_title({'name': 'Scatter Plot'})
        chart.set_x_axis({'name': 'X'})
        chart.set_y_axis({'name': 'Y'})
        chart.set_legend({'position': 'top'})
        chart_sheet.insert_chart('B2', chart, {'x_scale': 2, 'y_scale': 1.5})

def export_data_to_txt_evaluate(parent):
    """Export evaluation data to a TXT file (no index, headers repeated for obs/sim).
    
    Args:
        parent: GraphWindow instance.
    """
    plot_data = parent.plot_data

    options = QFileDialog.Options()
    file_path, _ = QFileDialog.getSaveFileName(parent, "Save Evaluate Data to TXT", "", "Text Files (*.txt);;All Files (*)", options=options)
    if not file_path:
        return

    vars_list = sorted(set(d['label'] for d in plot_data))
    if not vars_list:
        return

    obs_dict = {}
    sim_dict = {}
    n_rows = 0
    for d in plot_data:
        label = d['label']
        obs_dict[label] = d['y']
        sim_dict[label] = d['x']
        n_rows = max(n_rows, len(d['y']))

    col_widths = {v: max(len(v), max(len(str(val)) for val in obs_dict.get(v, []) + sim_dict.get(v, [])) + 2) for v in vars_list}

    with open(file_path, 'w') as f:
        f.write(f"File(s): {parent.filename}\n\n")
        header = ' '.join(v.ljust(col_widths[v]) for v in vars_list) + ' ' + ' '.join(v.ljust(col_widths[v]) for v in vars_list)
        f.write(header + '\n')
        for i in range(n_rows):
            obs_line = [obs_dict.get(v, [])[i] if i < len(obs_dict.get(v, [])) else '' for v in vars_list]
            sim_line = [sim_dict.get(v, [])[i] if i < len(sim_dict.get(v, [])) else '' for v in vars_list]
            line_parts = obs_line + sim_line
            line = ' '.join(str(val).ljust(col_widths[vars_list[j % len(vars_list)]]) for j, val in enumerate(line_parts))
            f.write(line + '\n')

def export_data_to_excel_evaluate(parent):
    """Export evaluation data to an Excel file with data, chart, and statistic sheet
    
    Args:
        parent: GraphWindow instance.
    """
    plot_data = parent.plot_data
    data = parent.data

    options = QFileDialog.Options()
    file_path, _ = QFileDialog.getSaveFileName(parent, "Save Evaluate Data & Graph to Excel", "", "Excel Files (*.xlsx);;All Files (*)", options=options)
    if not file_path:
        return

    vars_list = sorted(set(d['label'] for d in plot_data))
    if not vars_list:
        return

    obs_dict = {}
    sim_dict = {}
    n_rows = 0
    for d in plot_data:
        label = d['label']
        obs_dict[label] = d['y']
        sim_dict[label] = d['x']
        n_rows = max(n_rows, len(d['y']))

    # Data DF with repeated column names
    columns = [''] + vars_list + vars_list
    data_df = pd.DataFrame(columns=columns, index=range(n_rows))
    col_idx = 1
    for v in vars_list:
        data_df.iloc[:, col_idx] = [obs_dict.get(v, [])[i] if i < len(obs_dict.get(v, [])) else None for i in range(n_rows)]
        col_idx += 1
    for v in vars_list:
        data_df.iloc[:, col_idx] = [sim_dict.get(v, [])[i] if i < len(sim_dict.get(v, [])) else None for i in range(n_rows)]
        col_idx += 1

    # Statistic DF
    stats_df = pd.DataFrame(columns=[
        'Variable Name', 'Observed', 'Simulated', 'Ratio', 'Observed', 'Simulated',
        'r-Square', 'Mean Diff.', 'Mean Abs.Diff.', 'RMSE', 'd-Stat.', 'Used Obs.', 'Total Number Obs.'
    ])
    for v in vars_list:
        observed = obs_dict.get(v, [])
        simulated = sim_dict.get(v, [])
        stats = calculate_statistics(observed, simulated)
        if stats:
            row = [
                v,
                stats.get('mean_observed'),
                stats.get('mean_simulated'),
                stats.get('mean_ratio'),
                stats.get('std_observed'),
                stats.get('std_simulated'),
                stats.get('r_squared'),
                stats.get('mean_diff'),
                stats.get('mean_abs_diff'),
                stats.get('rmse'),
                stats.get('d_stat'),
                stats.get('used_obs'),
                stats.get('total_obs')
            ]
            stats_df.loc[len(stats_df)] = row

    with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
        workbook = writer.book
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'border': 1, 'align': 'center'})
        cell_format = workbook.add_format({'border': 1})

        # Data sheet
        data_df.to_excel(writer, sheet_name='Data', index=False, startrow=0, header=False)
        ws_data = writer.sheets['Data']
        # Write headers (repeated)
        for col_num, value in enumerate(columns):
            ws_data.write(0, col_num, value, header_format)
        for row_num in range(n_rows):
            for col_num in range(len(columns)):
                val = data_df.iloc[row_num, col_num]
                ws_data.write(row_num + 1, col_num, val if pd.notna(val) else '', cell_format)
        for col_num in range(len(columns)):
            max_len_col = max(len(str(columns[col_num])), data_df.iloc[:, col_num].astype(str).map(len).max())
            ws_data.set_column(col_num, col_num, max_len_col + 2)

        # Statistic sheet
        stats_df.to_excel(writer, sheet_name='Statistic', index=False, startrow=1)
        ws_stat = writer.sheets['Statistic']
        ws_stat.write(0, 0, '', header_format)  # Blank
        ws_stat.write(0, 1, 'Mean', header_format)
        ws_stat.write(0, 2, '', header_format)
        ws_stat.write(0, 3, '', header_format)
        ws_stat.write(0, 4, 'Std.Dev.', header_format)
        ws_stat.write(0, 5, '', header_format)
        ws_stat.write(0, 6, '', header_format)
        ws_stat.write(0, 7, '', header_format)
        ws_stat.write(0, 8, '', header_format)
        ws_stat.write(0, 9, '', header_format)
        ws_stat.write(0, 10, '', header_format)
        ws_stat.write(0, 11, '', header_format)
        ws_stat.write(0, 12, '', header_format)
        for col_num, col in enumerate(stats_df.columns):
            ws_stat.write(1, col_num, col, header_format)
        for row_num, row in stats_df.iterrows():
            for col_num, val in enumerate(row):
                ws_stat.write(row_num + 2, col_num, val if pd.notna(val) else '', cell_format)

        
        chart_sheet = workbook.add_worksheet('Plot')
        chart = workbook.add_chart({'type': 'scatter'})
        num_vars = len(vars_list)
        for idx, v in enumerate(vars_list):
            x_col_idx = 1 + idx  # obs columns start at 1
            y_col_idx = 1 + num_vars + idx  # sim after obs
            x_letter = xl_col_to_name(x_col_idx)
            y_letter = xl_col_to_name(y_col_idx)
            chart.add_series({
                'name': v,
                'categories': f"Data!${x_letter}$2:${x_letter}${n_rows + 1}",
                'values': f"Data!${y_letter}$2:${y_letter}${n_rows + 1}",
                'marker': {'type': 'circle', 'size': 6}
            })
        chart.set_title({'name': 'Evaluate Data (Simulated vs Measured)'})
        chart.set_x_axis({'name': 'Observed'})
        chart.set_y_axis({'name': 'Simulated'})
        chart.set_legend({'position': 'top'})
        chart_sheet.insert_chart('B2', chart, {'x_scale': 2, 'y_scale': 1.5})

def export_tfile_to_txt(plot_data, parent, use_calendar_mode=True):
 
    options = QFileDialog.Options()
    file_path, _ = QFileDialog.getSaveFileName(
        parent, "Save T File Data to TXT", "", "Text Files (*.txt);;All Files (*)", options=options
    )
    if not file_path:
        return

    x_key   = 'x_calendar' if use_calendar_mode else 'x_dap'
    x_label = 'Date' if use_calendar_mode else 'DAP'

    all_x = set()
    for ds in plot_data:
        all_x.update(ds.get(x_key, []))
    all_x = sorted(all_x)

    if use_calendar_mode and all_x:
        min_date = min(all_x)
        max_date = max(all_x)
        cur = min_date
        full = []
        while cur <= max_date:
            full.append(cur)
            cur += timedelta(days=1)
        all_x = full

    table = {}
    for ds in plot_data:
        label = ds.get('label', '???')
        xs    = ds.get(x_key, [])
        ys    = ds.get('y', [])
        for x, y in zip(xs, ys):
            if x not in table:
                table[x] = {}
            table[x][label] = y

    col_order = [ds.get('label', '???') for ds in plot_data]

    # Calculate widths dynamically for all columns, including x_label
    date_strs = []
    for x in all_x:
        if use_calendar_mode:
            # Assume x is datetime.date or datetime.datetime; strip time if present
            if hasattr(x, 'date'):
                x = x.date()
            date_strs.append(x.strftime('%m/%d/%Y'))
        else:
            date_strs.append(str(x))

    date_width = max(len(x_label), max((len(s) for s in date_strs), default=0)) + 2

    widths = {lbl: len(lbl) + 2 for lbl in col_order}
    for row in table.values():
        for lbl, val in row.items():
            widths[lbl] = max(widths[lbl], len(str(val)) + 2)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(f"File(s): {parent.filename}\n\n")

        header = x_label.ljust(date_width)
        for lbl in col_order:
            header += lbl.ljust(widths[lbl])
        f.write(header.rstrip() + "\n")

        for x, date_str in zip(all_x, date_strs):
            line = date_str.ljust(date_width)
            for lbl in col_order:
                val = table.get(x, {}).get(lbl, '')
                line += str(val).ljust(widths[lbl])
            f.write(line.rstrip() + "\n")


def export_tfile_to_excel(plot_data, parent, use_calendar_mode=True):
    """
    Export a *.T* file to Excel with data and plot
    """
    options = QFileDialog.Options()
    file_path, _ = QFileDialog.getSaveFileName(
        parent, "Save T File Data to Excel", "", "Excel Files (*.xlsx);;All Files (*)", options=options
    )
    if not file_path:
        return

    x_key   = 'x_calendar' if use_calendar_mode else 'x_dap'
    x_label = 'Date' if use_calendar_mode else 'DAP'

    all_x = set()
    for ds in plot_data:
        all_x.update(ds.get(x_key, []))
    all_x = sorted(all_x)

    # Detect if x values are Excel serial dates (integers/floats) or already datetime
    is_serial = all_x and isinstance(all_x[0], (int, float))

    def serial_to_dt(serial):
        return datetime(1899, 12, 30) + timedelta(days=int(serial))

    # Convert all_x to datetime if serial
    if use_calendar_mode and is_serial:
        all_x = [serial_to_dt(x) for x in all_x]

    # Build table with converted keys if necessary
    table = {}
    for ds in plot_data:
        lbl = ds.get('label', '???')
        xs = ds.get(x_key, [])
        if use_calendar_mode and is_serial:
            xs = [serial_to_dt(x) for x in xs]
        ys = ds.get('y', [])
        for x, y in zip(xs, ys):
            table.setdefault(x, {})[lbl] = y

    col_order = [ds.get('label', '???') for ds in plot_data]

    rows = []
    for x in all_x:
        row = {x_label: x}
        for lbl in col_order:
            row[lbl] = table.get(x, {}).get(lbl, None)
        rows.append(row)

    df = pd.DataFrame(rows)

    date_fmt = 'm/d/yyyy' if use_calendar_mode else None
    with pd.ExcelWriter(file_path, engine='xlsxwriter',
                        date_format=date_fmt) as writer:

        df.to_excel(writer, sheet_name='Data', index=False, startrow=0)

        workbook  = writer.book
        ws_data   = writer.sheets['Data']

        header_fmt = workbook.add_format({
            'bold': True, 'bg_color': '#D3D3D3',
            'border': 1, 'align': 'center'
        })
        cell_fmt = workbook.add_format({'border': 1})
        
        date_cell_fmt = workbook.add_format({'border': 1, 'num_format': 'mm/dd/yyyy'})

        for c, col in enumerate(df.columns):
            ws_data.write(0, c, col, header_fmt)

        for r, row in enumerate(df.itertuples(index=False), start=1):
            for c, val in enumerate(row):
                if c == 0 and use_calendar_mode and val is not None:
                    if isinstance(val, (date, datetime)):
                        dt_val = val if isinstance(val, datetime) else datetime(val.year, val.month, val.day)
                        ws_data.write_datetime(r, c, dt_val, date_cell_fmt)
                    else:
                        ws_data.write(r, c, val if pd.notnull(val) else '', cell_fmt)
                else:
                    ws_data.write(r, c, val if pd.notnull(val) else '', cell_fmt)

        for c, col in enumerate(df.columns):
            try:
                max_len = max(len(str(col)), df[col].astype(str).map(len).max())
            except Exception:
                max_len = len(str(col))
            ws_data.set_column(c, c, max_len + 2)

        chart_ws = workbook.add_worksheet('Plot')
        chart    = workbook.add_chart({'type': 'line'})

        for i, lbl in enumerate(col_order, start=1):     
            col_letter = xl_col_to_name(i)                
            chart.add_series({
                'name':       f"=Data!${col_letter}$1",
                'categories': f"=Data!$A$2:$A${len(df)+1}",
                'values':     f"=Data!${col_letter}$2:${col_letter}${len(df)+1}",
                'line':       {'width': 1.5}
            })

        chart.set_title({'name': 'T File Data'})
        chart.set_x_axis({
            'name': x_label,
            'date_axis': use_calendar_mode,
            'num_format': 'mm/dd/yyyy' if use_calendar_mode else '0',
            'label_position': 'low'
        })
        chart.set_y_axis({'name': 'Value'})
        chart.set_legend({'position': 'top'})
        chart_ws.insert_chart('B2', chart, {'x_scale': 2, 'y_scale': 1.5})