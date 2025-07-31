import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.font_manager as fm
import itertools

def build_plot_data(data, variable, run=None, use_calendar=True):
    """Build plot data for a specific variable, optionally filtered by run, with x-values in calendar or
    DAP (Days After Planting) mode.

    Args:
        data (list): List of data entries containing run, values, and variable information.
        variable (str): Variable code to filter data (e.g., 'cde').
        run (str, optional): Specific run to filter data. If None, all runs are included.
        use_calendar (bool): True to use calendar days mode, False to use DAP.
    Returns:
        list: List of dictionaries with x_calendar, y, label and type for plotting.
    """
    # Initialize dictionary to group data by run, variable and type.
    grouped = {}  

    # Iterate through data entries.
    for entry in data:
        # Skip entries not matching the specific run, if provided.
        if run and entry.get("run") != run:
            continue

        entry_run = entry.get("run")
        values = entry.get("values", [])

        # Process each variable entry in the values list.
        for var_entry in values:
            # Skip if variable code doesn't match.
            if var_entry.get("cde") != variable:
                continue
            
            # Extract type, values, x_calendar.
            val_type = var_entry.get("type")
            val_values = var_entry.get("values", [])
            x_calendar = var_entry.get("x_calendar", [])

            # Create unique key for grouping.
            key = (entry_run, variable, val_type)
            if key not in grouped:
                grouped[key] = {
                    "x": [],
                    "y": [],
                    "label": f"{variable} ({entry_run})",
                    "type": val_type
                }

            # Use calendar dates or DAP for x-values
            x_vals = x_calendar if use_calendar else list(range(1, len(val_values) + 1))
            grouped[key]["x"].extend(x_vals)
            grouped[key]["y"].extend(val_values)

    # Convert grouped data to list of plot data dictionaries.
    plot_data = []
    for group in grouped.values():
        plot_data.append({
            "x_calendar": group["x"],
            "y": group["y"],
            "label": group["label"],
            "type": group["type"]
        })
    return plot_data


def _apply_legend(ax, figure, plot_data, legend_visible):
    """Apply or remove the legend with custom formatting to the plot
    
    Args:
        ax: Matplotlib axis object.
        figure: Matplotlib figure object.
        plot_data (list): List of plot data dictionaries for legend labels.
        legend_visible (bool): True to show legend, False to hide it.
        """
    # Add legend with custom formatting
    figure.subplots_adjust(bottom=0.25)

    if legend_visible:
        # Calculate number of columns for legend (max 4, min 1)
        ncol = min(4, max(1, len(plot_data)//2)) 
        # Set small font size for legend
        small_font = fm.FontProperties(size=7)

        # Add legend with custom format
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
        # Remove legend if not visible
        ax.legend().remove()


def plot_time_series(figure, plot_data, use_calendar_mode=True, legend_visible=True):
    """Plot time series data with simulated lines and measured scatter points.
    
    Args:
        figure: Matplotlib figure object to plot on.
        plot_data (list): List of dictionaries with x_calendar, y, label, and type.
        use_calendar_mode (bool): True for calendar dates, False for DAP.
        legend_visible: Enables the legend when True, disables when false
    """
    
    # Clear figure and create new subplot
    figure.clear()
    ax = figure.add_subplot(111)

    # Extract unique variable labels and assign colors
    labels = [data['label'].split(' (')[0] for data in plot_data]
    unique_labels = list(dict.fromkeys(labels))
    colors = itertools.cycle(plt.cm.tab10.colors)
    label_to_color = {label: next(colors) for label in unique_labels}

    # Plot each dataset
    for data in plot_data:
        # Select x-values based on mode
        x_values = data['x_calendar'] if use_calendar_mode else data.get('x_dap', data['x_calendar'])
        y_values = data['y']
        label = data['label']
        cde = label.split(' (')[0]
        plot_type = data.get('type', 'simulated')
        color = label_to_color[cde]

        # validate data
        if not x_values or not y_values or len(x_values) != len(y_values):
            print(f"Warning: Invalid data for {label}: x={len(x_values)}, y={len(y_values)}")
            continue
        
        # Warn if all DAP values are 0 for measured data
        if not use_calendar_mode and plot_type == 'measured' and all(x == 0 for x in x_values):
            print(f"Warning: All x_dap values are 0 for measured data {label}. Check DAP calculation or planting date.")

        # Plot measured data as scatter, simulated as line
        if plot_type == 'measured':
            ax.scatter(x_values, y_values, label=label, color=color, marker='o', alpha=0.6)
        else:
            ax.plot(x_values, y_values, label=label, color=color, linestyle='-')

    # Set axis labels
    ax.set_xlabel('Calendar Day' if use_calendar_mode else 'Days After Planting')
    ax.set_ylabel('Value')
    ax.grid(True)

    # Format x-axis for calendar mode
    if use_calendar_mode:
        try:
            if x_values and not all(isinstance(x, (int, float)) for x in x_values):
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
                figure.autofmt_xdate()
        except Exception as e:
            print(f"Error formatting dates for calendar mode: {e}")
            ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{int(x)}"))

    # Apply legend formatting
    _apply_legend(ax, figure, plot_data, legend_visible)
    # Redraw canvas
    figure.canvas.draw()


def plot_scatter(figure, plot_data, legend_visible=True):
    """ Plot scatter data with x and y values for each dataset.
    
    Args:
        figure: Matplotlib figure object to plot on.
        plot_data (list): List of tuples containing (x_values, y_values, label)
        legend_visible (bool): True to show legend, False to hide it.    
    """
    # Clear figure and create new subplot
    figure.clear()
    ax = figure.add_subplot(111)

    # Plot each dataset as scatter
    for x_values, y_values, label in plot_data:
        ax.scatter(x_values, y_values, label=label)

    # Set axis labels
    ax.set_xlabel('X-Axis Variable')
    ax.set_ylabel('Y-Axis Variable')
    ax.grid(True)

    # Apply legend formatting
    _apply_legend(ax, figure, plot_data, legend_visible)
    # Redraw canvas
    figure.canvas.draw()


def plot_evaluate(figure, plot_data, legend_visible=True):
    """Plot evaluation scatter data comparing simulated vs measured values with optional expected values.
    
    Args: 
        figure: Matplotlib figure object to plot on.
        plot_data (list): List of dictionaries with x, y, y_expected, and label.
        legend_visible (bool): True to show legend, False to hide it.
    """
    # Clear figure and create new subplot
    figure.clear()
    ax = figure.add_subplot(111)

    # Assign unique markers and colors to labels
    marker_styles = ['s', '^', '+', '*', 'o', 'D', 'v', '<', '>']
    labels = [data['label'] for data in plot_data]
    unique_labels = list(dict.fromkeys(labels))
    label_to_marker = {label: marker_styles[i % len(marker_styles)] for i, label in enumerate(unique_labels)}
    colors = itertools.cycle(plt.cm.tab10.colors)
    label_to_color = {label: next(colors) for label in unique_labels}

    # Plot each dataset
    for data in plot_data:
        x_values = data['x']
        y_values = data['y']
        y_expected = data.get('y_expected', [None] * len(y_values))
        label = data['label']
        marker = label_to_marker[label]
        color = label_to_color[label]

        # Filter valid x and y values
        valid_x = [x for x in x_values if x is not None]
        valid_y = [y for y in y_values if y is not None]
        if valid_x and valid_y and len(valid_x) == len(valid_y):
            ax.scatter(valid_x, valid_y, marker=marker, color=color, label=label, alpha=0.6)

        # Filter valid expected y values
        valid_y_expected = []
        for i in range(min(len(y_expected), len(y_values))):
            if y_expected[i] is not None and (i >= len(y_values) or y_expected[i] != y_values[i]):
                valid_y_expected.append(y_expected[i])
        valid_x_expected = valid_x[:len(valid_y_expected)] if valid_y_expected else []
        if valid_y_expected and valid_x_expected:
            ax.scatter(valid_x_expected, valid_y_expected, marker=marker, facecolors='none', edgecolors=color, label=f'{label} (Expected)', alpha=0.6)
    # Set axis labels
    ax.set_xlabel('Simulated Data')
    ax.set_ylabel('Value')
    ax.grid(True)

    # Apply legend formatting
    _apply_legend(ax, figure, plot_data, legend_visible)
    # Redraw canvas
    figure.canvas.draw()
