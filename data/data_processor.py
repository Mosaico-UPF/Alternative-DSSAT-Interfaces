import os
import requests
from collections import defaultdict
from datetime import datetime

#Attempts to realize an absolut import, in case of failure, fallback to a relative path
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
                if line.startswith("EXP.") or "EXPERIMENT" in line.upper():#Checks for line starting with 'EXP.' or containing 'EXPERIMENT'
                    parts = line.split()
                    for part in parts:
                        if len(part) == 8 and part.isalnum(): #Returns first 8 chars alphanumeric part as exp code
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
            if not isinstance(data, list):
                print(f"Error: Expected list for T file {file_name}, got {type(data)}: {data}")
                return None, f"Invalid data format for T file {file_name}"
            # Add file type and mark values as measured
            for entry in data:
                entry["file_type"] = "t"
                for value in entry.get("values", []):
                    value["type"] = "measured"
            print(f"Loaded T file data ({file_name}): {len(data)} entries")
            return data, None
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
            print(f"Raw API response for {file_name}: {raw_json}")
            # Validate response is not a string
            if isinstance(raw_json, str):
                print(f"Error: Expected JSON object or list for Evaluate file {file_name}, got string: {raw_json}")
                return None, f"Invalid data format for Evaluate file {file_name}: string response"
            if not isinstance(raw_json, dict) or "results" not in raw_json:
                print(f"Error: Invalid response structure for Evaluate file {file_name}: {raw_json}")
                return None, f"Invalid response structure for Evaluate file {file_name}"
            normalized_data = []
            # Normalize results into a consistent format 
            for result in raw_json["results"]:
                if not isinstance(result, dict):
                    print(f"Error: Expected dict in results for Evaluate file {file_name}, got {type(result)}: {result}")
                    continue
                entry = {
                    "file_type": "evaluate",
                    "values": result  # Keep the full dictionary to preserve S/M pairs
                }
                normalized_data.append(entry)
            print(f"Loaded Evaluate file data ({file_name}): {len(normalized_data)} entries")
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

            #Validate OUT file data
            if not out_data or not isinstance(out_data, list):
                print(f"Error: Empty or invalid OUT file: {file_name}")
                return None, f"Empty or invalid OUT file: {file_name}"

            experiment = out_data[0].get("experiment")
            if not experiment:
                print("Warning: Experiment not found in OUT file header.")
                for entry in out_data:
                    entry["file_type"] = "out"
                return out_data, None

            # Use sim-vs-obs endpoint only for PlantGro.OUT, PlantN.OUT, SoilWat.OUT
            sim_vs_obs_files = ["plantgro.out", "plantn.out", "soilwat.out"]
            if file_name.lower() in sim_vs_obs_files:
                # Attempt to fetch observed data
                simvsobs_url = f"http://localhost:3000/api/sim-vs-obs/{crop_name}/{file_name}"
                try:
                    print(f"Trying Simulated vs Observed: {simvsobs_url}")
                    simvsobs_response = requests.get(simvsobs_url)
                    simvsobs_response.raise_for_status()
                    simvsobs_data = simvsobs_response.json()
                    print(f"Sim vs Obs data for {file_name}: {simvsobs_data}")

                    enriched_data = []
                    for run_entry in out_data:
                        run_name = run_entry.get("run", "Unknown")
                        treatment_number = run_entry.get("treatmentNumber", "Unknown")
                        print(f"Processing run: {run_name}, treatment: {treatment_number}")
                        run_obs = simvsobs_data.get(run_name) or simvsobs_data.get(treatment_number)
                        if not run_obs:
                            print(f"Warning: No observed data found for run {run_name} (treatment {treatment_number}) in {file_name}. Available keys: {list(simvsobs_data.keys())}")
                        
                        cde_group = {}
                        # Add simulated data
                        for sim in run_entry.get("values", []):
                            cde = sim.get("cde")
                            cde_group.setdefault(cde, []).append({
                                "cde": cde,
                                "values": sim.get("values", []),
                                "type": "simulated"
                            })

                        if run_obs:
                            observed_ts = run_obs.get("measured_time_series", [])
                            observed_final = run_obs.get("measured_final", {})
                            print(f"Observed data for run {run_name}: time_series={observed_ts}, final={observed_final}")
                            if not observed_ts and not observed_final:
                                print(f"Warning: No observed data found for run {run_name} (treatment {treatment_number}) in {file_name}")
                            else:
                                # Add observed final data
                                for cde, val in observed_final.items():
                                    print(f"Adding measured final variable: {cde} = {val}")
                                    cde_group.setdefault(cde, []).append({
                                        "cde": cde,
                                        "values": [val] if not isinstance(val, list) else val,
                                        "type": "measured"
                                    })
                                # Add observed time series data with x_calendar
                                for ts_entry in observed_ts:
                                    date_str = ts_entry.get("date")
                                    if date_str:
                                        try:
                                            x_calendar = [datetime.strptime(date_str, '%Y-%m-%d')]
                                            for cde, val in ts_entry.items():
                                                if cde.lower() in {"date", "day"}:
                                                    continue
                                                print(f"Adding measured time-series variable: {cde} = {val} at {date_str}")
                                                cde_group.setdefault(cde, []).append({
                                                    "cde": cde,
                                                    "values": [val] if not isinstance(val, list) else val,
                                                    "x_calendar": x_calendar,
                                                    "type": "measured"
                                                })
                                                # Add observed time series data with x_calendar
                                        except ValueError as e:
                                            print(f"Invalid date format for {date_str}: {e}")
                        else:
                            print(f"Warning: No observed data found for run {run_name} (treatment {treatment_number}) in {file_name}")

                        enriched_data.append({
                            "run": run_name,
                            "experiment": experiment,
                            "file_type": "out",
                            "values": [v for sub in cde_group.values() for v in sub]
                        })

                    print(f"Enriched data for {file_name}: {len(enriched_data)} entries")
                    return enriched_data, None

                except requests.RequestException as obs_err:
                    print(f"Warning: Failed to get observed data: {obs_err}")
                    for entry in out_data:
                        entry["file_type"] = "out"
                    return out_data, None
            else:
                # For other .out files, return the data without attempting sim-vs-obs
                for entry in out_data:
                    entry["file_type"] = "out"
                return out_data, None

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