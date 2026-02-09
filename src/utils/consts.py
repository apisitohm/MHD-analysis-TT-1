# src/utils/consts.py
from src.utils.config_manager import config_manager

# Load Config
_sys_conf = config_manager.get_config("system", {})
_analysis_conf = config_manager.get_config("analysis", {})

# Plotting Constants
FS = _sys_conf.get("fs", 200000.00)  # Sampling frequency

# Data Path
BASE_PATH = _sys_conf.get("data_path_base", r"./data/1275")
IP_ADDRESS = _sys_conf.get("ip_address", "127.0.0.1")    #MDSPlus Server IP
PORT = _sys_conf.get("port", 8000)                 #MDSPlus Server Port

# Default shot number
SHOT_NO = _sys_conf.get("default_shot_no", 1275)

# Default Data Method
DATA_METHOD = _sys_conf.get("default_method", "DAQ SV.")

# Default IP Signal
IP_SIGNAL = _sys_conf.get("default_ip_signal", "IP1")

# Setup Modes
MODE_POLOIDAL = "m" # Poloidal mode number of channels
MODE_TOROIDAL = "n" # Toroidal mode number of channels

# Default mode
MODE = "m"

# Signal Param Names
PARAM_POLOIDAL = "OBP" # Poloidal magnetic probe 12 channels at 30 degrees
PARAM_TOROIDAL = "M" # Toroidal magnetic probe 14 channels at 22.5 degrees

# Default Parameters
PARAM = "OBP"

# Default Suffix
SUFFIX = "N"

# Default Channels (Example, should be confirmed or dynamic)
# Assuming 14 channels for 'M' (n mode) and 12 for 'OBP' (m mode) based on context
NUM_CHANNELS_M = 14
NUM_CHANNELS_OBP = 12

# Default Window Size
WINDOW_SIZE = 200

# Default NFFT
NFFT = config_manager.get_config("analysis.spectrogram.default_nfft", 512)

# Default start time
START_TIME = 0

# Default end time
END_TIME = 10

# Default freq center
FREQ_CENTER = 10000 # 10 kHz

# Default freq width
FREQ_WIDTH = 3000 # 3 kHz

# Default param overlay
PARAM_OVERLAY = "IP1"

# Load PARAM_CONFIG from params.json
PARAM_CONFIG = config_manager.get_params()
