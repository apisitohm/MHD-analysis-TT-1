# src/data/loader.py
import numpy as np
import pandas as pd
import os
from mdsthin import Connection
from src.utils.config_manager import config_manager
_sys_config = config_manager.get_config("system",{})

# def load_shot_data(shotno, param_prefix, num_channels):
#     """
#     Loads data for a list of channels based on the prefix and number of channels.
#     Returns:
#         concatenated_data (np.ndarray): Shape (num_channels, time_steps)
#         time_array (np.ndarray): Time values
#     """
#     param_list = [f"{param_prefix}{i}T" for i in range(1, num_channels + 1)] # Assuming naming convention OBP1T, OBP2T... or M1T... 
#     pass

def load_txt_data(shotno, param_list, base_path=None):
    """
    Loads data for a list of channels based on the prefix and number of channels.
    Returns:
        concatenated_data (np.ndarray): Shape (num_channels, time_steps)
        time_array (np.ndarray): Time values
    """
    path = base_path if base_path else r'data'
    results = {}
    for param in param_list:
        try:
            data = pd.read_csv(os.path.join(path, f"{param}.txt"),sep=r'\s+',header=None,skiprows=8)
            raw_data = data.iloc[:,1].to_numpy(dtype=float)
            prof_time = data.iloc[:,0].to_numpy(dtype=float)
            results[param] = (raw_data, prof_time)
        except Exception as e:
            print(f"Error fetching {param}: {e}")
            results[param] = (None, None)
            
    return results
    


def load_mds_data(shotno, param_list):
    """
    Connects to MDSplus and fetches parameters.
    """
    # Using the logic from load_mdsplus.py
    results = {}
    try:
        IP_HOST = _sys_config.get("ip_address","")
        PORT = _sys_config.get("port",8000)
        con = Connection(f'{IP_HOST}:{PORT}')
        con.openTree('tt1', shotno)
        # Default path if none provided
        
        for param in param_list:
            # print(f"Loading {param}")
            try:
                raw_data = con.get(f"{param}").data()
                prof_time = con.get(f"DIM_OF({param})").data()
                results[param] = (raw_data, prof_time)
            except Exception as e:
                print(f"Error fetching {param}: {e}")
                results[param] = (None, None)
            # try:
            #     data = pd.read_csv(os.path.join(path, f"{param}.txt"),sep=r'\s+',header=None,skiprows=8)
            #     raw_data = data.iloc[:,1].to_numpy(dtype=float)
            #     prof_time = data.iloc[:,0].to_numpy(dtype=float)
            #     results[param] = (raw_data, prof_time)
            # except Exception as e:
            #     print(f"Error fetching {param}: {e}")
            #     results[param] = (None, None)
                
        con.closeTree('tt1', shotno)
        con.disconnect()
        
    except Exception as e:
        print(f"MDSplus Connection Error: {e}")
        return None

    return results

def fetch_mhd_data(shotno, method, mode, suffix='T', ip_signal='IP2', base_path=None):
    """
    High level function to get the array of data.
    mode: 'm' or 'n'
    suffix: 'N' or 'T'
    ip_signal: 'IP1' or 'IP2'
    base_path: Optional custom path to data files.
    """
    if mode == 'm':
        prefix = "OBP"
        # suffix = "N" # Overridden by arg
        num_channels = 12
    elif mode == 'n':
        prefix = "M"
        # suffix = "T" # Overridden by arg
        num_channels = 14
    else:
        return None, None, None, None

    param_list = [f"{prefix}{i}{suffix}" for i in range(1, num_channels + 1)]
    
    # Also fetch IP for duration calc
    param_list.append(ip_signal)
    if method == "DAQ SV.":
        data_dict = load_mds_data(shotno, param_list)
    else:
        data_dict = load_txt_data(shotno, param_list, base_path=base_path)
    
    if data_dict is None:
        return None, None, None, None

    # Process into array
    # Check first channel to get time and length
    first_key = f"{prefix}1{suffix}"
    if data_dict[first_key][0] is None:
        return None, None, None, None
        
    ref_data, ref_time = data_dict[first_key]
    time_len = len(ref_data)
    
    # Create matrix
    data_matrix = np.zeros((num_channels, time_len))
    
    for i in range(num_channels):
        key = f"{prefix}{i+1}{suffix}"
        val, _ = data_dict[key]
        if val is not None and len(val) == time_len:
            data_matrix[i, :] = val
        else:
            # Handle missing or mismatched data? fill with zeros or nan
            pass
            
            # Handle missing or mismatched data? fill with zeros or nan
            pass
            
    ip_data, ip_time = data_dict.get(ip_signal, (None, None))
    
    return data_matrix, ref_time, ip_data, ip_time
