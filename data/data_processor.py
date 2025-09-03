import os
import requests
from collections import defaultdict
from datetime import datetime

# Attempts to realize an absolute import, in case of failure, fallback to a relative path
try:
    from ..utils.t_files_dictionary import CROP_T_FILE_EXTENSIONS
    from ..utils.settings import get_plot_type
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from utils.t_files_dictionary import CROP_T_FILE_EXTENSIONS
    from utils.settings import get_plot_type

def read_experiment_code(file_path):
    """Try to read the experiment code from a .OUT file header (e.g., UFGA8201).
    
    Args:
        file_path (str): Path to the .OUT file.
    Returns:
        str or None: The experiment code if found, else None.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip() 
                if line.startswith("EXP.") or "EXPERIMENT" in line.upper():
                    parts = line.split()
                    for part in parts:
                        if len(part) == 8 and part.isalnum():
                            return part.upper()
        return None
    except Exception as e:
        print(f"Error reading experiment code: {e}")
        return None

def get_file_type(filename):
    """Determine the file type based on its extension.
    
    Args:
        filename (str): Name of the file
    Returns:
        str: File Type ('t', 'evaluate', '.out' or 'unknown')
    
    """
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
    """Load data from a single file using the API.
    
    Args:
        file_path (str): Path to the file
    Returns:
        tuple: (data, error_message) where data is loaded or None,
        and error_message is None or an error string.    
    """
    file_name = os.path.basename(file_path)
    file_ext = os.path.splitext(file_name)[1].lower()
    directory = os.path.dirname(file_path)
    
    # Handles FileT
    if file_ext in CROP_T_FILE_EXTENSIONS:
        crop_type = CROP_T_FILE_EXTENSIONS[file_ext]
        url = f"http://localhost:3000/api/t/{crop_type}/{file_name}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            # Validate that data is a list 
            normalized_data = []
            for entry in data:
                entry["file_type"] = "t"  # Already there
                values_list = []
                for cde, ts in entry.get("measuredTimeSeries", {}).items():
                    values_list.append({
                        "cde": cde,
                        "values": [float(v) if v != '-99' and v is not None else None for v in ts.get("values", [])],  # Handle -99 as None
                        "x_calendar": ts.get("dates", []),  # Keep as strings for now
                        "type": "measured"
                    })
                entry["values"] = values_list
                normalized_data.append(entry)
            print(f"Normalized T data: {normalized_data}")
            return normalized_data, None 
        except requests.RequestException as e:
            print(f"Error loading T file {file_name}: {str(e)}")
            return None, f"Error loading T file {file_name}: {str(e)}"

    # Handles evaluate.OUT files
    elif file_name.lower() == "evaluate.out":
        crop_name = os.path.basename(directory)
        url = f"http://localhost:3000/api/evaluate/{crop_name}/{file_name}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            raw_json = response.json()
            normalized_data = []
            for result in raw_json.get("results", []):
                entry = {
                    "run": f"Treatment_{result.get('TRNO', {}).get('value', 'Unknown')}",
                    "experiment": result.get("EXCODE", {}).get("value", "Unknown"),
                    "file_type": "evaluate",
                    "values": []
                }
                time_field = raw_json.get("timeField")
                for key, val in result.items():
                    if key == time_field or not isinstance(val, dict) or val.get("type") != "combined":
                        continue
                    if val["simulated"] is not None and val["simulated"] != -99:
                        entry["values"].append({
                            "cde": key,
                            "values": [float(val["simulated"])],
                            "x_calendar": [],  # Summary, no dates
                            "type": "simulated"
                        })
                    if val["measured"] is not None and val["measured"] != -99:
                        entry["values"].append({
                            "cde": key,
                            "values": [float(val["measured"])],
                            "x_calendar": [],  # Summary, no dates
                            "type": "measured"
                        })
                normalized_data.append(entry)
            print(f"Normalized Evaluate data: {normalized_data}")
            return normalized_data, None
        except requests.RequestException as e:
            print(f"Error loading Evaluate file {file_name}: {str(e)}")
            return None, f"Error loading Evaluate file {file_name}: {str(e)}"
        
    # Handle other .OUT files
    elif file_name.lower().endswith('.out'):
        crop_name = os.path.basename(directory)
        out_url = f"http://localhost:3000/api/out/{crop_name}/{file_name}"
        try:
            print(f"Requesting OUT URL: {out_url}")
            out_response = requests.get(out_url)
            out_response.raise_for_status()
            out_data = out_response.json()

            # Validate OUT file data
            if not out_data or not isinstance(out_data, list):
                print(f"Error: Empty or invalid OUT file: {file_name}")
                return None, f"Empty or invalid OUT file: {file_name}"

            experiment = out_data[0].get("experiment", "Unknown")
            if not experiment:
                print("Warning: Experiment not found in OUT file header.")

            # Use sim-vs-obs endpoint for PlantGro.OUT, PlantN.OUT, SoilWat.OUT
            sim_vs_obs_files = ["plantgro.out", "plantn.out", "soilwat.out"]
            enriched_data = []
            
            if file_name.lower() in sim_vs_obs_files:
                simvsobs_url = f"http://localhost:3000/api/sim-vs-obs/{crop_name}/{file_name}"
                try:
                    print(f"Trying Simulated vs Observed: {simvsobs_url}")
                    simvsobs_response = requests.get(simvsobs_url)
                    simvsobs_response.raise_for_status()
                    out_data = simvsobs_response.json()  # Use sim-vs-obs data
                    print(f"Sim vs Obs data for {file_name}: {len(out_data)} entries")
                except requests.RequestException as obs_err:
                    print(f"Warning: Failed to get sim-vs-obs data: {obs_err}")
                    # Fall back to out_data without measured data

            # Normalize data
            for run_entry in out_data:
                run_name = run_entry.get("run", f"Treatment_{run_entry.get('treatmentNumber', 'Unknown')}")
                entry = {
                    "run": run_name,
                    "experiment": run_entry.get("experiment", experiment),
                    "file_type": run_entry.get("fileType", "out").lower(),
                    "values": []
                }

                # Add simulated data (time-series)
                for cde, sim in run_entry.get("simulated", {}).items():
                    values = sim.get("values", [])
                    dates = sim.get("dates", [])
                    if values:  # Only include if non-empty
                        entry["values"].append({
                            "cde": cde,
                            "values": [float(v) if v is not None and v != -99 and not isinstance(v, str) else None for v in values],
                            "x_calendar": dates,  # Keep as strings
                            "type": "simulated"
                        })

                # Add measured final data (single values)
                for cde, meas in run_entry.get("measuredFinal", {}).items():
                    value = meas.get("value")
                    if value is not None and value != -99:
                        entry["values"].append({
                            "cde": cde,
                            "values": [float(value)],
                            "x_calendar": [],
                            "type": "measured"
                        })

                # Add measured time-series data (full arrays)
                for cde, ts in run_entry.get("measuredTimeSeries", {}).items():
                    values = ts.get("values", [])
                    dates = ts.get("dates", [])
                    if values:  # Only include if non-empty
                        entry["values"].append({
                            "cde": cde,
                            "values": [float(v) if v is not None and v != '-99' and v != -99 else None for v in values],
                            "x_calendar": dates,
                            "type": "measured"
                        })

                if entry["values"]:  # Only append if there are values
                    enriched_data.append(entry)
                else:
                    print(f"Warning: No valid data for run {run_name} in {file_name}")

            if not enriched_data:
                print(f"Error: No valid data processed for {file_name}")
                return None, f"No valid data processed for {file_name}"

            print(f"Normalized OUT data for {file_name}: {len(enriched_data)} entries")
            return enriched_data, None

        except requests.RequestException as e:
            print(f"Error loading OUT file {file_name}: {str(e)}")
            return None, f"Error loading OUT file {file_name}: {str(e)}"

    else:
        print(f"Error: Unsupported file type: {file_name}")
        return None, f"Unsupported file type: {file_name}"
    
    
def load_all_file_data(file_paths):
    """Load data from multiple files and return combined data.
    
    Args:
        file_paths (list): List of file paths to load.
    Returns:
        tuple: (combined_data, error_message) where combined_data is a list
        of data entries and error_message is None or an error string.
    """
    all_data = []
    t_file_count = 0
    for file_path in file_paths:
        file_name = os.path.basename(file_path)
        # Check for multiple T files
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
    return all_data, None

def extract_runs_and_variables(data):
    """Extract unique runs and variables from the data.
    
    Args:
        data(list): List of data entries.
    Returns:
        tuple: (sorted_runs, sorted_variables) where sorted_runs is a sorted
        list of run names and sorted_variables is a sorted list of variable names
    """
    runs = set()
    variables = set()

    for entry in data:
        if not entry or not isinstance(entry, dict):
            continue
        
        # Extract run name
        run = entry.get('run', 'Unknown')
        runs.add(run)

        values = entry.get('values', [])

        # Extract variables from list of dictionaries 
        if isinstance(values, list):
            for variable in values:
                if isinstance(variable, dict):
                    cde = variable.get('cde')
                    if cde:
                        variables.add(cde)
                        print(f"Extracted variable: {cde}")

        # Extract variable from dictionary
        elif isinstance(values, dict):
            for key in values:
                variables.add(key)

    return sorted(list(runs)), sorted(list(variables))