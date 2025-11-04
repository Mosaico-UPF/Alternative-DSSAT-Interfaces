# tests/test_data_processor.py
import pytest
import requests
from data.data_processor import (
    get_file_type, load_file_data, load_all_file_data, extract_runs_and_variables
)


def test_get_file_type():
    assert get_file_type("file.MZT") == "t"
    assert get_file_type("Evaluate.OUT") == "evaluate"
    assert get_file_type("PlantGro.OUT") == "out"
    assert get_file_type("unknown.txt") == "unknown"


def test_load_file_data_t_file(mocker):
    # --- Success case ---
    mock_response = mocker.Mock()
    mock_response.json.return_value = [
        {
            "measuredTimeSeries": {
                "TEST_CDE": {
                    "values": [1.0, 2.0],
                    "dates": ["2023-01-01", "2023-01-02"]
                }
            }
        }
    ]
    mock_response.raise_for_status.return_value = None

    mocker.patch("requests.get", return_value=mock_response)

    data, error = load_file_data("any/path/test.MZT")
    assert error is None
    assert len(data) == 1
    assert data[0]["values"][0]["cde"] == "TEST_CDE"
    assert data[0]["values"][0]["values"] == [1.0, 2.0]

    # --- Error case (new patch, no overwrite) ---
    mocker.patch("requests.get", side_effect=requests.RequestException("Network error"))
    data, error = load_file_data("any/path/test.MZT")
    assert data is None
    assert "Error loading T file" in error


def test_load_all_file_data_multiple_t_files(mocker):
    # Patch get_file_type to return "t" so files are recognized
    mocker.patch("data.data_processor.get_file_type", return_value="t")

    # We don't need to call load_file_data — early exit happens
    data, error = load_all_file_data(["file1.t", "file2.t"])

    assert data == []
    assert error == "Only one .t file is allowed to be selected."


def test_extract_runs_and_variables():
    sample = [
        {
            "run": "Run1",
            "values": [
                {"cde": "LAI", "values": [1.0], "type": "simulated"},
                {"cde": "BIOM", "values": [100], "type": "simulated"},
            ],
        },
        {
            "run": "Run2",
            "values": [{"cde": "LAI", "values": [1.1], "type": "simulated"}],
        },
    ]
    runs, variables = extract_runs_and_variables(sample)
    assert runs == ["Run1", "Run2"]
    assert variables == ["BIOM", "LAI"]