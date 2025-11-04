import numpy as np
from scipy.stats import linregress

def extract_normalized_series(data, variable, run=None):
    measured = {}
    simulated = {}

    for entry in data:
        if run and entry.get("run") != run:
            continue

        values = entry.get("values", [])
        for var_entry in values:
            if var_entry.get("cde") != variable:
                continue

            typ = var_entry.get("type")
            vals = var_entry.get("values", [])
            dates = var_entry.get("x_calendar") or list(range(len(vals)))

            if typ == "measured":
                measured.update(dict(zip(dates, vals)))
            elif typ == "simulated":
                simulated.update(dict(zip(dates, vals)))

    common = sorted(set(measured) & set(simulated))
    obs = [float(measured[k]) if measured[k] is not None else None for k in common]
    sim = [float(simulated[k]) if simulated[k] is not None else None for k in common]

    return obs, sim



def calculate_statistics(observed, simulated):

    if len(observed) != len(simulated):
        return None

    

    pairs = [(o, s) for o, s in zip(observed, simulated)
             if o is not None and s is not None]

    if not pairs:
        return None

    
    filtered = [(o, s) for o, s in pairs if o != 0]

    if not filtered:
        return None

    obs_arr = np.array([p[0] for p in filtered])
    sim_arr = np.array([p[1] for p in filtered])

   
    used_obs = len(filtered)                               
    total_obs = sum(1 for v in observed if v is not None and v != 0)  



    mean_obs = np.mean(obs_arr)
    mean_sim = np.mean(sim_arr)
    mean_ratio = mean_sim / mean_obs if mean_obs != 0 else np.nan


    std_obs = np.std(obs_arr, ddof=1) if len(obs_arr) > 1 else 0.0
    std_sim = np.std(sim_arr, ddof=1) if len(sim_arr) > 1 else 0.0


    if len(obs_arr) > 1:
        slope, intercept, r_val, _, _ = linregress(obs_arr, sim_arr)
        r_square = r_val ** 2
    else:
        r_square = np.nan


    diff = sim_arr - obs_arr
    mean_diff = np.mean(diff)
    mean_abs_diff = np.mean(np.abs(diff))
    rmse = np.sqrt(np.mean(diff ** 2))


    o_mean = np.mean(obs_arr)
    numerator = np.sum(diff ** 2)
    denominator = np.sum((np.abs(sim_arr - o_mean) + np.abs(obs_arr - o_mean)) ** 2)
    d_stat = 1.0 - (numerator / denominator) if denominator != 0 else 1.0

 
    return {
        # Header 1
        'mean_observed':   int(round(mean_obs)),          
        'mean_simulated':  int(round(mean_sim)),           
        'mean_ratio':      round(mean_ratio, 3),         

        # Header 2
        'std_observed':    round(std_obs, 3),              
        'std_simulated':   round(std_sim, 3),             
        'r_squared':       round(r_square, 3),             

        # Header 3
        'mean_diff':       int(round(mean_diff)),         
        'mean_abs_diff':   int(round(mean_abs_diff)),    
        'rmse':            round(rmse, 3),                 
        'd_stat':          round(d_stat, 3),              

        # Footer
        'used_obs':        used_obs,                      
        'total_obs':       total_obs                       
    }