# C:\Users\User\Documents\Projetos\interface_Gbuild_refatorada\data\data_processor.py
import os
import requests
from collections import defaultdict

# Relative import for CROP_T_FILE_EXTENSIONS
try:
    from ..utils.t_files_dictionary import CROP_T_FILE_EXTENSIONS
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from utils.t_files_dictionary import CROP_T_FILE_EXTENSIONS

def get_file_type(filename):
    """Determine the file type based on its extension."""
    ext = os.path.splitext(filename.lower())[1]
    if ext in CROP_T_FILE_EXTENSIONS:
        return "t"
    elif ext == ".out":
        if "evaluate" in filename.lower() and filename.lower().endswith(".out"):
            return "evaluate"
        return "out"
    else:
        return "unknown"

def load_file_data(file_path):
    """Load data from a single file using the API."""
    file_name = os.path.basename(file_path)
    file_ext = os.path.splitext(file_name)[1].lower()
    directory = os.path.dirname(file_path)

    # Determine the URL
    if file_ext in CROP_T_FILE_EXTENSIONS:
        crop_type = CROP_T_FILE_EXTENSIONS[file_ext]
        url = f"http://localhost:3000/api/t/{crop_type}/{file_name}"
    elif file_name.lower() == "evaluate.out":
        crop_name = os.path.basename(directory)
        url = f"http://localhost:3000/api/evaluate/{crop_name}/{file_name}"
    elif file_name.lower().endswith('.out'):
        crop_name = os.path.basename(directory)
        url = f"http://localhost:3000/api/out/{crop_name}/{file_name}"
    else:
        return None, f"Unsupported file type: {file_name}"

    try:
        print(f"Requesting URL: {url}")
        response = requests.get(url)
        response.raise_for_status()

        if response.text.strip() == "":
            return None, f"No data returned for file: {file_name}"

        file_type = get_file_type(file_name)

        # Parse and normalize
        if file_type == "evaluate":
            raw_json = response.json()
            if "results" not in raw_json:
                return None, f"Invalid response structure for file: {file_name}"

            normalized_data = []
            for result in raw_json["results"]:
                entry = {
                    "file_type": "evaluate",
                    "values": result  # Keep the full dictionary to preserve S/M pairs
                }
                normalized_data.append(entry)

            return normalized_data, None
        else:
            file_data = response.json()
            if file_data is None:
                return None, f"Invalid response for file: {file_name}"

            # Add file type to each entry
            for entry in file_data:
                if isinstance(entry, dict):
                    entry["file_type"] = file_type

            return file_data, None

    except requests.RequestException as e:
        return None, f"Error accessing the API for file {file_name}: {str(e)}"

def load_all_file_data(file_paths):
    """Load data from multiple files and return combined data."""
    all_data = []
    t_file_count = 0
    for file_path in file_paths:
        file_name = os.path.basename(file_path)
        if get_file_type(file_name) == "t":
            t_file_count += 1
            if t_file_count > 1:
                return [], "Only one .t file is allowed to be selected."
        data, error = load_file_data(file_path)
        if error:
            print(error)
            continue
        if data:
            all_data.extend(data)
    return all_data, None  # Always return a tuple

def extract_runs_and_variables(data):
    """Extract unique runs and variables from the data."""
    runs = set()
    variables = set()

    for entry in data:
        if not entry or not isinstance(entry, dict):
            continue

        run = entry.get('run', 'Unknown')
        runs.add(run)

        values = entry.get('values', [])

        # Case 1: old format (.T or .OUT), list of dicts
        if isinstance(values, list):
            for variable in values:
                if isinstance(variable, dict):
                    cde = variable.get('cde')
                    if cde:
                        variables.add(cde)

        # Case 2: evaluate.out format, flat dictionary
        elif isinstance(values, dict):
            for key in values:
                variables.add(key)

    return sorted(list(runs)), sorted(list(variables))
