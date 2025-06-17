# C:\Users\User\Documents\Projetos\interface_Gbuild_refatorada\plots\plotting.py
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import itertools

def plot_time_series(figure, plot_data, use_calendar_mode=True, legend_visible=True):
    figure.clear()
    ax = figure.add_subplot(111)

    labels = [data['label'] for data in plot_data]
    unique_labels = list(dict.fromkeys(labels))
    colors = itertools.cycle(plt.cm.tab10.colors)
    label_to_color = {label: next(colors) for label in unique_labels}

    for data in plot_data:
        x_values = data['x_calendar'] if use_calendar_mode else data.get('x_dap', data['x_calendar'])
        y_values = data['y']
        label = data['label']  # fix here
        color = label_to_color[label]

        if len(y_values) == 1:  # Single point: use scatter
            ax.scatter(x_values, y_values, label=label, color=color)
        else:  # Multiple points: use plot
            ax.plot(x_values, y_values, label=label, color=color)

    ax.set_xlabel('Calendar Day' if use_calendar_mode else 'Days After Planting')
    ax.set_ylabel('Value')
    ax.grid(True)

    if use_calendar_mode:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        figure.autofmt_xdate()

    if legend_visible:
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    else:
        ax.legend().remove()

    figure.canvas.draw()

def plot_scatter(figure, plot_data, legend_visible=True):
    figure.clear()
    ax = figure.add_subplot(111)

    for x_values, y_values, label in plot_data:
        ax.scatter(x_values, y_values, label=label)

    ax.set_xlabel('X-Axis Variable')
    ax.set_ylabel('Y-Axis Variable')
    if legend_visible:
        ax.legend()
    else:
        ax.legend().remove()
    figure.canvas.draw()

def plot_evaluate(figure, plot_data, legend_visible=True):
    figure.clear()
    ax = figure.add_subplot(111)

    # Define marker styles for different variables
    marker_styles = ['s', '^', '+', '*', 'o', 'D', 'v', '<', '>']  # squares, triangles, plus, star, circle, diamond, etc.
    labels = [data['label'] for data in plot_data]
    unique_labels = list(dict.fromkeys(labels))
    label_to_marker = {label: marker_styles[i % len(marker_styles)] for i, label in enumerate(unique_labels)}
    colors = itertools.cycle(plt.cm.tab10.colors)
    label_to_color = {label: next(colors) for label in unique_labels}

    # Plot each variable's data
    for data in plot_data:
        x_values = data['x']  # Simulated data
        y_values = data['y']  # Measured or fallback data
        y_expected = data.get('y_expected', [None] * len(y_values))  # Expected values
        label = data['label']
        marker = label_to_marker[label]
        color = label_to_color[label]

        # Plot simulated data
        valid_x = [x for x in x_values if x is not None]
        valid_y = [y for y in y_values if y is not None]
        if valid_x and valid_y and len(valid_x) == len(valid_y):
            ax.scatter(valid_x, valid_y, marker=marker, color=color, label=f'{label}', alpha=0.6)
        elif not valid_x or not valid_y:
            print(f"Warning: No valid data points for {label}")

        # Plot expected data if available and different from y_values
        valid_y_expected = []
        for i in range(min(len(y_expected), len(y_values))):
            if y_expected[i] is not None and (i >= len(y_values) or y_expected[i] != y_values[i]):
                valid_y_expected.append(y_expected[i])
        valid_x_expected = valid_x[:len(valid_y_expected)] if valid_y_expected else []
        if valid_y_expected and valid_x_expected:
            ax.scatter(valid_x_expected, valid_y_expected, marker=marker, facecolors='none', edgecolors=color, label=f'{label} (Expected)', alpha=0.6)

    ax.set_xlabel('Simulated Data')
    ax.set_ylabel('Value')
    ax.grid(True)

    if legend_visible and any(data.get('label') for data in plot_data):  # Only show legend if there are labeled artists
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    else:
        ax.legend().remove()

    figure.canvas.draw()