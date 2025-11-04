# tests/test_stats_calculator.py
import pytest
import numpy as np
from utils.stats_calculator import extract_normalized_series, calculate_statistics


@pytest.fixture
def sample_data():
    return [
        {
            "run": "TestRun",
            "values": [
                {
                    "cde": "TEST_VAR",
                    "values": [1.0, 2.0, None, 4.0],
                    "x_calendar": ["2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04"],
                    "type": "measured",
                },
                {
                    "cde": "TEST_VAR",
                    "values": [1.1, 2.1, 3.1, 4.1],
                    "x_calendar": ["2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04"],
                    "type": "simulated",
                },
            ],
        }
    ]


def test_extract_normalized_series(sample_data):
    obs, sim = extract_normalized_series(sample_data, "TEST_VAR", run="TestRun")
    # None values are **kept** in the series (the function does NOT filter them)
    assert obs == [1.0, 2.0, None, 4.0]
    assert sim == [1.1, 2.1, 3.1, 4.1]

    # No matching run → empty lists
    obs, sim = extract_normalized_series(sample_data, "TEST_VAR", run="Wrong")
    assert obs == []
    assert sim == []


def test_calculate_statistics():
    # Perfect 1-to-1 offset of 0.1
    obs = [1.0, 2.0, 3.0]
    sim = [1.1, 2.1, 3.1]

    stats = calculate_statistics(obs, sim)

    assert stats["mean_observed"] == 2
    assert stats["mean_simulated"] == 2
    # 2.1 / 2.0 = 1.05
    assert stats["mean_ratio"] == pytest.approx(1.05, rel=1e-3)

    assert stats["r_squared"] == pytest.approx(1.0, rel=1e-3)
    assert stats["rmse"] == pytest.approx(0.1, rel=1e-3)

    # used / total observations
    assert stats["used_obs"] == 3
    assert stats["total_obs"] == 3


def test_calculate_statistics_with_zero():
    # Zero in observed is filtered out
    obs = [0.0, 1.0, 2.0]
    sim = [0.1, 1.1, 2.1]

    stats = calculate_statistics(obs, sim)
    assert stats["used_obs"] == 2
    assert stats["total_obs"] == 2