
import numpy as np
import time
import tracemalloc
import sys
import os
import shutil
import tempfile
import pandas as pd
from scipy.ndimage import zoom

# Ensure src is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.analysis import SignalProcessor
from src.utils.config_manager import config_manager
from src.data.loader import load_txt_data

def generate_synthetic_data(duration_sec=0.5, fs=200000.0, num_channels=12):
    """Generates synthetic MHD-like data (sine waves + noise)."""
    t = np.linspace(0, duration_sec, int(duration_sec * fs))
    data = np.zeros((num_channels, len(t)))
    
    # Generate rotating mode (m=2, n=1 like)
    freq = 10000.0 # 10 kHz
    for ch in range(num_channels):
        phase_offset = 2 * np.pi * ch / num_channels
        signal = np.sin(2 * np.pi * freq * t + phase_offset)
        noise = np.random.normal(0, 0.1, len(t))
        data[ch, :] = signal + noise
        
    return t, data

def benchmark_function(name, func, *args, **kwargs):
    print(f"\n--- Benchmarking: {name} ---")
    
    tracemalloc.start()
    start_time = time.perf_counter()
    
    try:
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        duration_ms = (end_time - start_time) * 1000
        peak_mb = peak / 1024 / 1024
        
        print(f"  Execution Time: {duration_ms:.4f} ms")
        print(f"  Peak Memory:    {peak_mb:.4f} MB")
        
        return result
    except Exception as e:
        print(f"  FAILED: {e}")
        tracemalloc.stop()
        return None

def benchmark_loader():
    print("\n--- Benchmarking: Loader (Text File) ---")
    
    # Create temp dir
    with tempfile.TemporaryDirectory() as tmpdirname:
        # Create dummy text files
        num_files = 12
        num_samples = 100000
        
        print(f"  Creating {num_files} dummy files with {num_samples} samples each...")
        
        # Format similar to expected input: 8 header lines, then space separated data
        # Col 0: Time, Col 1: Data
        t = np.linspace(0, 0.1, num_samples)
        data = np.sin(2 * np.pi * 1000 * t)
        
        df = pd.DataFrame({'Time': t, 'Data': data})
        
        header = "\n" * 8
        
        for i in range(1, num_files + 1):
            fname = os.path.join(tmpdirname, f"OBP{i}T.txt")
            with open(fname, 'w') as f:
                f.write(header)
            
            df.to_csv(fname, sep=' ', header=False, index=False, mode='a')
            
        param_list = [f"OBP{i}T" for i in range(1, num_files + 1)]
        
        # Benchmark
        benchmark_function("load_txt_data", load_txt_data, 1275, param_list, base_path=tmpdirname)

def benchmark_config():
    print("\n--- Benchmarking: Config Manager ---")
    
    def access_config_repeatedly(n=10000):
        val = 0
        for _ in range(n):
            # Access deep key
            val = config_manager.get_config("analysis.spectrogram.noverlap_ratio")
        return val

    benchmark_function("Config Access (10k times)", access_config_repeatedly)

def benchmark_ui_zoom(data):
    print("\n--- Benchmarking: UI Zoom (Wavelet Smoothing) ---")
    
    # Simulate data used in WaveletWidget
    # Input is (Time, Channels) usually for image item? 
    # WaveletWidget update_plot says: data_matrix shape (Time, Channel)
    # But generate_synthetic_data returns (Channels, Time).
    # Let's transpose for the test.
    data_T = data.T # (Samples, Channels)
    
    # Slice a reasonable window like UI (e.g. 1000 samples)
    data_slice = data_T[:1000, :]
    
    def run_zoom():
        # zoom(input, zoom, order=3)
        # Zoom Y (channels) by 10
        return zoom(data_slice, (1, 10), order=3)
        
    benchmark_function("scipy.ndimage.zoom (1000x12 -> 1000x120)", run_zoom)

def run_benchmarks():
    print("Initializing Comprehensive Benchmark Suite...")
    print(f"System: {sys.platform}")
    
    # 1. Generate Data
    print("Generating Synthetic Data (0.5s @ 200kHz, 12 channels)...")
    t, data = generate_synthetic_data()
    print(f"Data Shape: {data.shape}, Size: {data.nbytes / 1024 / 1024:.2f} MB")
    
    # 2. Analysis Benchmarks
    ip_data = np.abs(data[0]) * 10000 
    benchmark_function("cal_duration", SignalProcessor.cal_duration, ip_data, t)
    
    benchmark_function("compute_spectrogram", SignalProcessor.compute_spectrogram, data[0], 200000.0)
    
    t_start = 0.1
    t_end = 0.2
    fbase = 10000.0
    dfreq = 3000.0
    benchmark_function("compute_wavelet_data", SignalProcessor.compute_wavelet_data, 
                       data, t, t_start, t_end, fbase, dfreq, fs=200000.0)
    
    # SVD
    slice_idx = int(0.01 * 200000)
    data_slice = data[:, :slice_idx]
    benchmark_function("compute_svd", SignalProcessor.compute_svd, data_slice)
    
    spatial_mode = np.random.random(12)
    benchmark_function("compute_spatial_structure", SignalProcessor.compute_spatial_structure, spatial_mode, num_coils=12)
    
    # 3. Loader Benchmarks
    benchmark_loader()
    
    # 4. Config Benchmarks
    benchmark_config()
    
    # 5. UI Benchmarks
    benchmark_ui_zoom(data)
    
    print("\nBenchmark Suite Completed.")

if __name__ == "__main__":
    run_benchmarks()
