# C:\Users\User\Documents\Projetos\interface_Gbuild_refatorada\utils\stats_calculator.py
import numpy as np
from scipy.stats import pearsonr

def calculate_statistics(observed, simulated):
    """Calculate statistical measures for observed vs simulated data."""
    n_obs = len(observed)
    if n_obs == 0 or len(simulated) != n_obs:
        return None

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

def get_variable_data(data, variable):
    """Extract observed and simulated values for a given variable from the data."""
    observed = []
    simulated = []
    for entry in data:
        if isinstance(entry, dict) and 'values' in entry:
            values = entry['values']
            if isinstance(values, dict) and variable in values:
                value_dict = values[variable]
                if 'measured' in value_dict and value_dict['measured'] is not None:
                    observed.append(value_dict['measured'])
                if 'simulated' in value_dict and value_dict['simulated'] is not None:
                    simulated.append(value_dict['simulated'])
    return observed, simulated