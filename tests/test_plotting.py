# tests/test_plotting.py
import pytest
from datetime import datetime
from plots.plotting import build_plot_data, _get_color_map


@pytest.fixture
def sample_data():
    return [
        {
            "run": "Run1",
            "values": [
                {
                    "cde": "TEST",
                    "values": [1.0, 2.0],
                    "x_calendar": ["2023-01-01", "2023-01-02"],
                    "type": "simulated",
                },
                {
                    "cde": "PDAT",
                    "values": [0],
                    "x_calendar": ["2023-01-01"],
                    "type": "simulated",
                },
            ],
        },
        {
            "run": "Run1",
            "values": [
                {
                    "cde": "TEST",
                    "values": [1.1, None],
                    "x_calendar": ["2023-01-01", "2023-01-02"],
                    "type": "measured",
                }
            ],
        },
    ]


def test_build_plot_data(sample_data):
    groups = build_plot_data(sample_data, "TEST", run="Run1")
    assert len(groups) == 2

    sim = next(g for g in groups if g["type"] == "simulated")
    meas = next(g for g in groups if g["type"] == "measured")

    assert sim["x_calendar"] == [datetime(2023, 1, 1), datetime(2023, 1, 2)]
    assert sim["x_dap"] == [0, 1]
    assert sim["y"] == [1.0, 2.0]

    assert meas["y"] == [1.1]


def test_get_color_map():
    # Use "label" instead of "variable" to match production code fallback
    plot_data = [
        {"label": "VAR1 Run1", "run": "Run1"},
        {"label": "VAR1 Run2", "run": "Run2"},
        {"label": "VAR2 Run1", "run": "Run1"},
    ]
    cmap = _get_color_map(plot_data)
    assert len(cmap) == 3
    assert cmap[("VAR1", "Run1")] != cmap[("VAR1", "Run2")]