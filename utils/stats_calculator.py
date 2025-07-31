import numpy as np
from scipy.stats import pearsonr

def calculate_statistics(observed, simulated):
    """Calculate statistical measures for observed vs simulated data.
    
    Args:
        observed (list): List of observed values.
        simulated (list): List of simulated values.
    
    Returns:
        dict: Statistical measures (mean, std dev, r-square, etc.) or None if invalid input.
    """
    # Validate input data
    n_obs = len(observed)
    if n_obs == 0 or len(simulated) != n_obs:
        return None

    # Calculate basic statistics
    mean_obs = np.mean(observed)
    mean_sim = np.mean(simulated)
    mean_ratio = mean_sim / mean_obs if mean_obs != 0 else float('nan')
    std_dev_obs = np.std(observed)
    std_dev_sim = np.std(simulated)
    mean_diff = mean_sim - mean_obs
    mean_abs_diff = np.mean(np.abs(np.array(simulated) - np.array(observed)))
    rmse = np.sqrt(np.mean((np.array(simulated) - np.array(observed)) ** 2))
    
    # r-Square (using Pearson correlation)
    corr, _ = pearsonr(observed, simulated)
    r_square = corr ** 2 if not np.isnan(corr) else float('nan')
    
    # d-stat (Willmott's index of agreement)
    diff = np.array(simulated) - np.array(observed)
    d_stat = 1 - (np.sum(diff ** 2) / np.sum((np.abs(diff) + np.abs(diff)) ** 2)) if n_obs > 0 else float('nan')
    
    # Return formatted statistics dictionary
    return {
        'Mean (Obs)': round(mean_obs, 2),
        'Mean (Sim)': round(mean_sim, 2),
        'Mean Ratio': round(mean_ratio, 2) if not np.isnan(mean_ratio) else 'N/A',
        'Std.Dev (Obs)': round(std_dev_obs, 2),
        'Std.Dev (Sim)': round(std_dev_sim, 2),
        'r-Square': round(r_square, 2) if not np.isnan(r_square) else 'N/A',
        'Mean Diff.': round(mean_diff, 2),
        'Mean Abs. Diff.': round(mean_abs_diff, 2),
        'RMSE': round(rmse, 2),
        'd-stat': round(d_stat, 2) if not np.isnan(d_stat) else 'N/A',
        'Used Obs.': n_obs,
        'Total Number': n_obs
    }

def get_variable_data(data, variable, run=None):
    """Extract observed and simulated values for a given variable from the data.
    
    Args: 
        data (list): List of data entries containing run and variable information
        variable (str): Variable code (CDE) to extract.
        run (str, optional): Specific run to filter by.
        
    Returns:
        tuple: (observed values, simulated values) as lists.
    """
    observed = []
    simulated = []
    
    for entry in data:
        # Filter by run if specified
        if run and entry.get("run") != run:
            continue
        
        if isinstance(entry, dict) and 'values' in entry:
            values = entry['values']
            
            # Handle evaluate.out format (values as dict with measured/simulated)
            if isinstance(values, dict) and variable in values:
                value_dict = values[variable]
                if 'measured' in value_dict and value_dict['measured'] is not None:
                    try:
                        observed.append(float(value_dict['measured']))
                    except (ValueError, TypeError):
                        continue
                if 'simulated' in value_dict and value_dict['simulated'] is not None:
                    try:
                        simulated.append(float(value_dict['simulated']))
                    except (ValueError, TypeError):
                        continue
            
            # Handle .out format (values as list with cde and type)s
            elif isinstance(values, list):
                obs_vals = None
                sim_vals = None
                for var_entry in values:
                    if isinstance(var_entry, dict) and var_entry.get('cde') == variable:
                        if var_entry.get('type') == 'measured':
                            obs_vals = var_entry.get('values', [])
                        elif var_entry.get('type') == 'simulated':
                            sim_vals = var_entry.get('values', [])
                
                if obs_vals and sim_vals:
                    min_len = min(len(obs_vals), len(sim_vals))
                    for i in range(min_len):
                        try:
                            o = float(obs_vals[i])
                            s = float(sim_vals[i])
                            observed.append(o)
                            simulated.append(s)
                        except (ValueError, TypeError):
                            continue
    
    return observed, simulated

def extract_normalized_series(data, variable, run=None):
    """Extract normalized observed and simulated series for a variable, aligned by calendar or index.
    
    Args: 
        data (list): List of data entries containing run and variable information.
        variable (str): Variable code (CDE) to extract.
        run (str, optional): Specific run to filter by.
    
    Returns:
        tuple: (observed values, simulated values) aligned by common calendar or index keys.
    """
    measured_points = []
    simulated_points = []

    for entry in data:
        # Filter by run if specified
        if run and entry.get("run") != run:
            continue

        values = entry.get("values", [])
        for var_entry in values:
            if var_entry.get("cde") != variable:
                continue

            val_type = var_entry.get("type")
            val_values = var_entry.get("values", [])
            x_calendar = var_entry.get("x_calendar", [])

            # Pair values with calendar dates or indexes
            if val_type == "measured":
                measured_points = list(zip(x_calendar, val_values)) if x_calendar else list(enumerate(val_values))
            elif val_type == "simulated":
                simulated_points = list(zip(x_calendar, val_values)) if x_calendar else list(enumerate(val_values))

    # Aligned measured and simulated data by common keys
    measured_dict = dict(measured_points)
    simulated_dict = dict(simulated_points)
    common_keys = sorted(set(measured_dict) & set(simulated_dict))

    observed = [float(measured_dict[k]) for k in common_keys]
    simulated = [float(simulated_dict[k]) for k in common_keys]

    return observed, simulated