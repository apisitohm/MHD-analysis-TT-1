
import sys
import os
import numpy as np

# Adjust path to find src
sys.path.append(os.getcwd())

from src.utils.config_manager import config_manager
from src.utils import consts
from src.data.analysis import SignalProcessor

def verify():
    print("Verifying Config Loading...")
    
    # 1. Verify Config Manager
    cal_dur = config_manager.get_config("analysis.cal_duration.threshold_factor")
    if cal_dur != 0.095:
        print(f"FAIL: analysis.cal_duration.threshold_factor is {cal_dur}, expected 0.095")
    else:
        print("PASS: analysis.cal_duration.threshold_factor = 0.095")
        
    # 2. Verify Consts
    if consts.FS != 200000.0:
        print(f"FAIL: consts.FS is {consts.FS}, expected 200000.0")
    else:
        print(f"PASS: consts.FS = {consts.FS}")
        
    if consts.PARAM_CONFIG.get('GBP1T', {}).get('unit') != 'T':
        print("FAIL: consts.PARAM_CONFIG not loaded correctly")
    else:
        print("PASS: consts.PARAM_CONFIG loaded from params.json")
        
    print("Verification Completed.")

if __name__ == "__main__":
    verify()
