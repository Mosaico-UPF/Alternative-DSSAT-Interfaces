import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.font_manager as fm
import itertools
from datetime import datetime

def build_plot_data(data, variable_cde, run=None, use_calendar=True):
    """
    Build plot data entries for a given variable (CDE) and optional run filter.
    Always computes both calendar x-values (datetimes) and DAP x-values.
    The `use_calendar` flag is ignored for construction and only used by the plotter to pick an axis.
    """
    def _parse_date(d):
        # Accept iso strings or already-datetime
        if isinstance(d, datetime):
            return d
        if isinstance(d, str):
            try:
                # support YYYY-MM-DD; ignore index- placeholders
                if d.lower().startswith("index-"):
                    return None
                return datetime.fromisoformat(d)
            except Exception:
                return None
        return None

    plot_groups = []
    # Determine a planting date per run
    planting_date_by_run = {}

    # First pass: discover planting dates
    for entry in (e for e in data if isinstance(e, dict)):
        entry_run = entry.get("run", "Unknown")
        if run and entry_run != run:
            continue
        if entry_run in planting_date_by_run:
            continue

        # Prefer PDAT if present with dates
        pdat_dates = []
        for v in entry.get("values", []):
            if v.get("cde", "").upper() == "PDAT":
                for d in (v.get("x_calendar") or []):
                    dt = _parse_date(d)
                    if dt:
                        pdat_dates.append(dt)
                break
        if pdat_dates:
            planting_date_by_run[entry_run] = min(pdat_dates)
            continue

        # Fallback: earliest date across any variable’s x_calendar in this run
        all_dates = []
        for v in entry.get("values", []):
            for d in (v.get("x_calendar") or []):
                dt = _parse_date(d)
                if dt:
                    all_dates.append(dt)
        planting_date_by_run[entry_run] = min(all_dates) if all_dates else None

    # Second pass: build series for requested variable
    for entry in (e for e in data if isinstance(e, dict)):
        entry_run = entry.get("run", "Unknown")
        if run and entry_run != run:
            continue

        for var in entry.get("values", []):
            cde = var.get("cde")
            if (cde or "").upper() != (variable_cde or "").upper():
                continue

            y_vals = var.get("values") or []
            if not y_vals:
                continue

            # Skip single-value entries without calendar (e.g., measuredFinal summary values)
            raw_calendar = var.get("x_calendar") or []
            if not raw_calendar and len(y_vals) == 1:
                print(f"Skipping summary value without date for {cde} ({var.get('type')}) in run {entry_run}")
                continue

            # Parse x_calendar; if missing, try to use a best-effort range
            x_calendar_dates = [_parse_date(d) for d in raw_calendar]
            # Keep alignment
            n = min(len(y_vals), len(x_calendar_dates)) if x_calendar_dates else len(y_vals)
            y_vals = y_vals[:n]
            x_calendar_dates = x_calendar_dates[:n] if x_calendar_dates else [None] * n

            # Compute DAP using per-run planting date; fall back to index if we lack dates
            pdate = planting_date_by_run.get(entry_run)
            if pdate and any(x_calendar_dates):
                x_dap = [ (d - pdate).days if isinstance(d, datetime) else None for d in x_calendar_dates ]
                # If a point lacks a date, fall back to index at that position
                x_dap = [i if x is None else x for i, x in enumerate(x_dap)]
            else:
                # No usable dates → index-based DAP
                x_dap = list(range(n))

            # Filter out points where y is None
            valid = [i for i in range(n) if y_vals[i] is not None]
            if not valid:
                print(f"Skipping {cde} ({var.get('type')}) in run {entry_run} due to no valid y values")
                continue
            x_calendar_dates = [x_calendar_dates[i] for i in valid]
            x_dap = [x_dap[i] for i in valid]
            y_vals = [y_vals[i] for i in valid]

            plot_groups.append({
                "x_calendar": x_calendar_dates,
                "x_dap": x_dap,
                "y": y_vals,
                "label": f"{cde} ({var.get('type')}) ({entry_run})",
                "type": var.get("type", "simulated"),
                "run": entry_run,
                "variable": cde
            })

    return plot_groups

def _get_color_map(plot_data):
    """Assign distinct colors based on (variable, run) combinations."""
    keys = list(dict.fromkeys([
        (data.get("variable", data["label"].split()[0]), data.get("run", "Unknown"))
        for data in plot_data
    ]))
    # Use Set1 for up to 9 distinct keys; otherwise fallback to tab20b+tab20c
    if len(keys) <= 9:
        base_colors = plt.cm.get_cmap("Set1").colors
    else:
        base_colors = plt.cm.get_cmap("tab20b").colors + plt.cm.get_cmap("tab20c").colors
    colors = itertools.cycle(base_colors)
    return {key: next(colors) for key in keys}

def _apply_legend(ax, figure, plot_data, legend_visible):
    """Apply or remove the legend with custom formatting."""
    figure.subplots_adjust(bottom=0.25)
    if legend_visible:
        ncol = min(4, max(1, len(plot_data) // 2))
        small_font = fm.FontProperties(size=7)
        ax.legend(
            loc='upper center',
            bbox_to_anchor=(0.5, -0.2),
            ncol=ncol,
            frameon=False,
            prop=small_font,
            handletextpad=0.3,
            borderpad=0.2,
            labelspacing=0.2
        )
    else:
        if ax.get_legend():
            ax.get_legend().remove()

def plot_time_series(figure, plot_data, use_calendar_mode=True, legend_visible=True):
    """Plot time series data with simulated lines and measured scatter points."""
    figure.clear()
    ax = figure.add_subplot(111)

    key_to_color = _get_color_map(plot_data)

    for data in plot_data:
        x_values = data['x_calendar'] if use_calendar_mode else data['x_dap']
        y_values = data['y']
        label = data['label']
        plot_type = data.get('type', 'simulated')
        run = data.get('run', 'Unknown')
        var = data.get('variable', data['label'].split()[0])
        color = key_to_color[(var, run)]

        if not x_values or not y_values or len(x_values) != len(y_values):
            print(f"Warning: Invalid data for {label}: x={len(x_values)}, y={len(y_values)}")
            continue

        valid_pairs = [(x, y) for x, y in zip(x_values, y_values) if x is not None and y is not None]
        if not valid_pairs:
            print(f"Warning: No valid data for {label}")
            continue
        x_values, y_values = zip(*valid_pairs)

        if not use_calendar_mode and plot_type == 'measured' and all(x == 0 for x in x_values):
            print(f"Warning: All x_dap values are 0 for {label}. Check DAP calculation or planting date.")

        if plot_type == 'measured':
            ax.scatter(x_values, y_values, label=label, color=color, marker='o', alpha=0.6)
        else:
            ax.plot(x_values, y_values, label=label, color=color, linestyle='-')

    ax.set_xlabel('Calendar Day' if use_calendar_mode else 'Days After Planting')
    ax.set_ylabel('Value')
    ax.grid(True)

    if use_calendar_mode:
        try:
            if x_values and any(isinstance(x, datetime) for x in x_values):
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
                figure.autofmt_xdate()
            else:
                ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{int(x)}"))
        except Exception as e:
            print(f"Error formatting dates for calendar mode: {e}")
            ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{int(x)}"))

    _apply_legend(ax, figure, plot_data, legend_visible)
    figure.canvas.draw()

def plot_evaluate(figure, plot_data, legend_visible=True):
    """Plot evaluation scatter data."""
    figure.clear()
    ax = figure.add_subplot(111)

    key_to_color = _get_color_map(plot_data)

    for data in plot_data:
        x_values = data['x']
        y_values = data['y']
        y_expected = data.get('y_expected', [None] * len(y_values))
        label = data['label']
        run = data.get('run', 'Unknown')
        var = data.get('variable', data['label'].split()[0])
        color = key_to_color[(var, run)]

        valid_pairs = [(x, y) for x, y in zip(x_values, y_values) if x is not None and y is not None]
        if not valid_pairs:
            print(f"Warning: No valid data for {label}")
            continue
        valid_x, valid_y = zip(*valid_pairs)

        ax.scatter(valid_x, valid_y, marker='o', color=color, label=label, alpha=0.6)

        valid_expected_pairs = [
            (x, y_exp) for x, y_exp in zip(x_values, y_expected)
            if x is not None and y_exp is not None and y_exp not in y_values
        ]
        if valid_expected_pairs:
            valid_x_exp, valid_y_exp = zip(*valid_expected_pairs)
            ax.scatter(valid_x_exp, valid_y_exp, marker='o', facecolors='none', edgecolors=color, label=f'{label} (Expected)', alpha=0.6)

    ax.set_xlabel('Simulated Data')
    ax.set_ylabel('Measured Data')
    ax.grid(True)

    _apply_legend(ax, figure, plot_data, legend_visible)
    figure.canvas.draw()

def plot_scatter(figure, plot_data, legend_visible=True):
    """Plot scatter data."""
    figure.clear()
    ax = figure.add_subplot(111)

    key_to_color = _get_color_map(plot_data)

    for data in plot_data:
        run = data.get("run", "Unknown")
        var = data.get("variable", data["label"].split()[0])
        color = key_to_color[(var, run)]
        x_values, y_values, label = data["x"], data["y"], data["label"]

        valid_pairs = [(x, y) for x, y in zip(x_values, y_values) if x is not None and y is not None]
        if not valid_pairs:
            print(f"Warning: No valid data for {label}")
            continue
        valid_x, valid_y = zip(*valid_pairs)
        ax.scatter(valid_x, valid_y, label=label, color=color)

    ax.set_xlabel('X-Axis Variable')
    ax.set_ylabel('Y-Axis Variable')
    ax.grid(True)

    _apply_legend(ax, figure, plot_data, legend_visible)
    figure.canvas.draw()
