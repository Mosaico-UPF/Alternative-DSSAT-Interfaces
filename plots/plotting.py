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
        label = data['label']
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

    for data in plot_data:
        x_values = data['x']
        y_values = data['y']
        label = data['label']
        ax.bar(x_values, y_values, label=label)

    ax.set_xlabel('Index')
    ax.set_ylabel('Value')
    if legend_visible:
        ax.legend()
    else:
        ax.legend().remove()
    figure.canvas.draw()