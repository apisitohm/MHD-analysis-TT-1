# src/data/analysis.py
import numpy as np
import scipy.signal as sigproc
from scipy.signal import spectrogram, savgol_filter
from scipy.interpolate import splprep, splev
from src.utils.config_manager import config_manager

# Load Config
_analysis_conf = config_manager.get_config("analysis", {})


class SignalProcessor:
    @staticmethod
    def cal_duration(data, time):
        """
        Calculates plasma duration based on IP signal.
        Logic adapted from original analysis.py
        """
        if data is None or time is None:
            return 0, 0, 0
            
        _conf = _analysis_conf.get("cal_duration", {})
        threshold_factor = _conf.get("threshold_factor", 0.095)
        min_val = _conf.get("min_val", 2500)
        
        threshold = threshold_factor * np.max(data) # Amp
        
        # Ensure data meets minimum criteria
        valid_indices = (data > threshold) & (data >= min_val)
        if not np.any(valid_indices):
            return 0, 0, 0

        # Find start
        start_idx = np.argmax(valid_indices)
        
        # Find end (search from reverse)
        # Note: argmax on boolean array returns index of first True
        end_idx_rev = np.argmax(valid_indices[::-1])
        end_idx = len(data) - end_idx_rev - 1
        
        start_time, end_time = time[start_idx], time[end_idx]
        print(f"DEBUG: cal_duration: threshold={threshold:.2f}, max_data={np.max(data):.2f}")
        print(f"DEBUG: cal_duration: start_idx={start_idx}, start_time={start_time}")
        print(f"DEBUG: cal_duration: end_idx={end_idx}, end_time={end_time}")
        
        duration = 0
        min_start_time_thresh = _conf.get("min_start_time_threshold", 300)
        if start_time >= min_start_time_thresh: 
            duration = end_time - start_time
        else:
            print(f"DEBUG: Start time {start_time} < 300, setting duration 0? (User Logic)")
            # Maybe default to calculating it anyway?
            duration = end_time - start_time
            
        return duration, np.max(data), start_idx # Returned 3 values to match unpacking

    @staticmethod
    def compute_spectrogram(data, fs, nperseg=None, noverlap=None, nfft=512, window_ms=None):
        """
        Computes spectrogram for a single channel data.
        window_ms: Window size in milliseconds (overrides nperseg if provided).
        """
        if window_ms is not None:
             nperseg = int(window_ms * fs / 1000.0)
             
        if nperseg is None:
            nperseg = int(0.001 * fs) # 1ms window default
        if noverlap is None:
            _conf = _analysis_conf.get("spectrogram", {})
            overlap_ratio = _conf.get("noverlap_ratio", 0.5)
            noverlap = int(nperseg * overlap_ratio) # Default from config
            
        freq, times, Sxx = spectrogram(data, fs, nperseg=nperseg, noverlap=noverlap, nfft=nfft)
        return freq, times, Sxx

    @staticmethod
    def norm_signal(data, width):
        return np.clip(data, -width, width)
        
    @staticmethod
    def freq_filter_savgol(signal, sos_filter, window_length=None):
        """
        Filters signal using SOS filter and then Savitzky-Golay filter.
        """
        _conf = _analysis_conf.get("savgol", {})
        _wave_conf = _analysis_conf.get("wavelet", {})
        if window_length is None:
            window_length = _wave_conf.get("savgol_window_default", 11)
        polyorder = _conf.get("polyorder", 3)
        """
        Filters signal using SOS filter and then Savitzky-Golay filter.
        Signal shape: (time_steps, channels) or (channels, time_steps)?
        Ref `spectro.py` implies processing one by one or array.
        Ref `wavelet.py`: `freq_filter_savgol(norm_.T, ...)` implies (time, ch) input?
        Let's assume input is (N_samples,) or (N_samples, N_ch).
        """
        filtered_signal = signal.copy()
        
        # Check specific length for sosfiltfilt (needs > padlen, usually ~3*order)
        # Order 16 -> padlen ~ 50-100
        min_len = _conf.get("min_len_for_filter", 100) 
        
        if filtered_signal.shape[0] < min_len:
            # Too short to filter effectively with high order
            return filtered_signal 

        # If 1D
        if filtered_signal.ndim == 1:
            try:
                filtered_signal = sigproc.sosfiltfilt(sos_filter, filtered_signal)
                if len(filtered_signal) > window_length:
                    filtered_signal = savgol_filter(filtered_signal, window_length=window_length, polyorder=polyorder)
            except Exception as e:
                print(f"Filter error 1D: {e}")
            return filtered_signal
            
        # If 2D (Sample x Channel)
        for i in range(filtered_signal.shape[1]):
            try:
                col_data = filtered_signal[:,i]
                if len(col_data) >= min_len:
                    col_data = sigproc.sosfiltfilt(sos_filter, col_data)
                
                if len(col_data) > window_length:
                    col_data = savgol_filter(col_data, window_length=window_length, polyorder=polyorder)
                
                filtered_signal[:,i] = col_data
            except Exception as e:
                print(f"Filter error 2D ch {i}: {e}")
                
        return filtered_signal

    @staticmethod
    def compute_wavelet_data(data_matrix, time_array, t_start, t_end, fbase, dfreq, fs=200000.0, excluded_channels=[]):
        """
        Computes data for wavelet plot (actually seems to be Bandpass + Contour plot in original code, not true Wavelet Transform).
        Original code `Wavelet_Plot` uses `sigproc.iirfilter` bandpass then plots contour.
        
        Args:
            data_matrix: (Channels, Time)
            time_array: (Time,)
            t_start, t_end: Time range
            fbase: Center frequency
            dfreq: Bandwidth (+/-)
        """
        # print(f"DEBUG: compute_wavelet_data inputs:")
        # print(f"  t_start={t_start}, t_end={t_end}, fbase={fbase}, dfreq={dfreq}")
        # if data_matrix is not None:
        #     print(f"  data_matrix shape={data_matrix.shape}")
        # else:
        #     print("  data_matrix is None")
        
        # if time_array is not None and len(time_array) > 0:
        #     print(f"  time_array range={time_array[0]} to {time_array[-1]}")
        # else:
        #     print("  time_array is None or empty")

        # Time slicing
        idx_ti = np.searchsorted(time_array, t_start)
        idx_tf = np.searchsorted(time_array, t_end)
        
        # print(f"  idx_ti={idx_ti}, idx_tf={idx_tf}, num_points={idx_tf - idx_ti}")
        
        # Ensure we have enough data points
        _conf = _analysis_conf.get("wavelet", {})
        min_len_filter = _analysis_conf.get("savgol", {}).get("min_len_for_filter", 100)
        
        if idx_tf - idx_ti < min_len_filter: 
            pass 

        if idx_ti >= idx_tf:
            return None, None
            
        sliced_time = time_array[idx_ti:idx_tf]
        sliced_data = data_matrix[:, idx_ti:idx_tf]
        
        # Check length for filter safety
        n_samples = sliced_data.shape[1]
        
        # Default order
        order_default = _conf.get("filter_order_default", 16)
        order = order_default
        
        # Adjust order for short signals to avoid padding errors
        # Typical padlen is related to order.
        if n_samples < 400:
            order = _conf.get("filter_order_medium", 4)
        if n_samples < 100:
            order = _conf.get("filter_order_short", 2) 
            
        # Norm
        norm_width = _conf.get("norm_width", 0.5)
        norm_data = SignalProcessor.norm_signal(sliced_data, norm_width)
        # norm_data = sliced_data.copy()
        
        # Filter
        low_margin = _conf.get("filter_low_margin", 100)
        low = max(low_margin, fbase - dfreq)
        high = min(fs/2 - low_margin, fbase + dfreq)
        
        try:
            _iir_conf = _analysis_conf.get("iirfilter", {})
            btype = _iir_conf.get("btype", "bandpass")
            output_type = _iir_conf.get("output", "sos")
            
            
            sos = sigproc.iirfilter(order, [low, high], fs=fs, btype=btype, output=output_type)
            
            # Savgol window logic
            winsize = _conf.get("winsize_default", 11)
            winsize_short = _conf.get("winsize_short", 5)
            min_samples_short = _conf.get("min_samples_short", 11)
            min_samples_very_short = _conf.get("min_samples_very_short", 5)

            if n_samples <= min_samples_short:
                winsize = winsize_short
            if n_samples <= min_samples_very_short:
                return sliced_time, norm_data.T 
            
            # Call without extra args (they are loaded inside)
            filtered_data_T = SignalProcessor.freq_filter_savgol(norm_data.T, sos, winsize)
            return sliced_time, filtered_data_T
            
        except Exception as e:
            print(f"Wavelet Filter Error (N={n_samples}, Order={order}): {e}")
            return sliced_time, norm_data.T 
        
    @staticmethod
    def calculate_phase_diffs(data_matrix, time_array, t1, t2, fbase, mode='m'):
        """
        Calculates phase differences for linear fit.
        
        Args:
            data_matrix: (Channels, Time)
            time_array: (Time) - Expected in MS if t1, t2 are in MS.
            t1, t2: Time range selected by user (MS).
            fbase: Frequency (Hz).
            mode: 'm' or 'n' to determine angles.
            
        Returns:
            angles (np.array): Coil locations in degrees.
            dphase (np.array): Phase differences in degrees.
        """
        if data_matrix is None or time_array is None:
            return None, None
            
        # Define range
        t_start = min(t1, t2)
        t_end = max(t1, t2)
        
        idx_ti = np.searchsorted(time_array, t_start)
        idx_tf = np.searchsorted(time_array, t_end)
        
        if idx_tf <= idx_ti:
            return None, None
            
        sliced_time = time_array[idx_ti:idx_tf]
        sliced_data = data_matrix[:, idx_ti:idx_tf]
        
        # Find peaks
        num_channels = data_matrix.shape[0]
        peak_times = np.zeros(num_channels)
        
        # Iterate channels
        for i in range(num_channels):
            ch_data = sliced_data[i, :]
            local_idx = np.argmax(ch_data) # finding max
            peak_times[i] = sliced_time[local_idx]
            
        # Calculate Phase Diff
        # Ref: Ch 1
        t0 = peak_times[0]
        dtime = peak_times - t0
        dphase = 360 * fbase * dtime
        
        if mode == 'n': # 14 channels?
             angles = np.linspace(0, 360 * (13/14), 14)
        else: # 12 channels
             angles = np.linspace(0, 330, 12)
             
        # Ensure exact 12 matches data shape
        if len(angles) != num_channels:
             # Fallback
             angles = np.linspace(0, 360 * ((num_channels-1)/num_channels), num_channels)
             
        return angles, dphase

    @staticmethod
    def calculate_phase_diffs_robust(peaks_list, p1, p2, fbase, num_coils=12, excluded_channels=[]):
        """
        Calculates phase differences using slope-based peak snapping.
        
        Args:
            peaks_list: list of dict {'t': time, 'ch': channel_index} from find_all_peaks
            p1, p2: dict {'t': time, 'ch': channel} (Selected points)
            fbase: Frequency (Hz)
            num_coils: Number of coils (12 or 14)
            excluded_channels: list of int identifiers to exclude
            
        Returns:
            angles (np.array): Coil locations in degrees.
            dphase (np.array): Phase differences in degrees.
            fitted_times (np.array): The actual time points used (for debug/plot).
        """
        if not peaks_list:
            return None, None, None
            
        # Group peaks by channel
        # channel indices are 1-based in peaks_list
        peaks_by_channel = {i: [] for i in range(1, num_coils + 1)}
        for p in peaks_list:
            if 1 <= p['ch'] <= num_coils:
                peaks_by_channel[p['ch']].append(p['t'])
                
        # Sort each channel's peaks
        for ch in peaks_by_channel:
            peaks_by_channel[ch].sort()
            
        # Define Line
        t_ref, ch_ref = p2['t'], p2['ch']
        t_final, ch_final = p1['t'], p1['ch']
        
        # Avoid division by zero
        if t_final == t_ref:
            return None, None, None
            
        m = (ch_final - ch_ref) / (t_final - t_ref)
        b = ch_ref - m * t_ref
        
        y_values = np.arange(1, num_coils + 1, 1)
        
        # Predict x (time) for each channel y
        if m == 0:
            return None, None, None
             
        x_pred = (y_values - b) / m
        
        result_times = []
        valid_indices = [] # indices 0..(num_coils-1) corresponding to channels 1..num_coils
        
        for i in range(num_coils):
            ch_idx = i + 1
            if ch_idx in excluded_channels:
                continue
                
            actual_peaks = peaks_by_channel[ch_idx]
            if not actual_peaks:
                continue
                
            pred_t = x_pred[i]
            
            # Find nearest
            idx_nearest = np.argmin(np.abs(np.array(actual_peaks) - pred_t))
            nearest_t = actual_peaks[idx_nearest]
            
            result_times.append(nearest_t)
            valid_indices.append(i)
            
        if not result_times:
            return None, None, None
            
        # Calculate Phase Diff
        result_times = np.array(result_times)
        dphase = 2 * np.pi * fbase * 1e-3 * np.abs(result_times - result_times[0]) * 180 / np.pi
        
        # Calculate Angles (Loc)
        # deg = np.arange(0,360,360/num_coils)
        # deg = np.delete(deg, excluded)
        
        all_deg = np.linspace(0, 360 * ((num_coils-1)/num_coils), num_coils)
        # Or np.arange(0, 360, 360/num_coils) -> 0, 30, ... 330 for 12 coils.
        
        loc = all_deg[valid_indices]
        
        return loc, dphase, result_times

    @staticmethod
    def find_all_peaks(time_array, data_matrix, distance=None):
        """
        Finds all peaks in the data matrix.
        
        Args:
            time_array: (Time,)
            data_matrix: (Channels, Time)
            distance: Min distance between peaks (indices).
            
        Returns:
            list of dict: [{'t': time, 'ch': channel_index, 'val': value}, ...]
        """
        if data_matrix is None or time_array is None:
            return []
            
        peaks_list = []
        num_channels = data_matrix.shape[0]
        
        for ch_idx in range(num_channels):
            # Using simple max finding or actual peak finding?
            # User said: "my program will use sample not too much to find peak and plot it"
            # And "user will select 2 point from that figure"
            # So likely we want ALL local maxima to show propagation.
            
            # Simple peak finding
            ch_data = data_matrix[ch_idx]
            
            # Use distance to avoid noise?
            # Default distance 10 samples?
            dist = distance if distance is not None else 10
            
            peak_indices, _ = sigproc.find_peaks(ch_data, distance=dist)
            
            for p_idx in peak_indices:
                peaks_list.append({
                    't': time_array[p_idx],
                    'ch': ch_idx + 1, # 1-based index for display? Or 0? Widget usually expects Y coordinate.
                    'val': ch_data[p_idx]
                })
                
        return peaks_list
    
    @staticmethod
    def find_wavelet_peaks(time_array, data_matrix):
        """
        Finds peaks in the data matrix for "Plot Max" visualization.
        
        Args:
            time_array: (Time,)
            data_matrix: (Channels, Time) or (Time, Channels). 
                         compute_wavelet_data returns (Time, Channels).
        
        Returns:
            points_data: List of dicts [{'pos': (t, ch), 'brush': color}, ...] or arrays for ScatterPlot
        """
        if time_array is None or data_matrix is None:
            return [], [], []
            
        # Ensure data is (Channels, Time) for easier iteration
        if data_matrix.shape[0] != len(time_array):
             # mostly likely (Ch, Time)
             pass
        else:
             # (Time, Ch) -> Transpose
             data_matrix = data_matrix.T
             
        num_channels = data_matrix.shape[0]
        
        all_times = []
        all_channels = []
        all_amps = []
        
        import scipy.signal as signal
        
        for i in range(num_channels):
            # Find positive peaks
            # Height threshold? Maybe simplistic 0?
            # Distance?
            peaks, properties = signal.find_peaks(data_matrix[i, :], height=0)
            
            if len(peaks) > 0:
                t_peaks = time_array[peaks]
                amps = properties['peak_heights']
                
                all_times.extend(t_peaks)
                all_channels.extend([i+1] * len(peaks)) # Channel 1-n
                all_amps.extend(amps)
                
        return np.array(all_times), np.array(all_channels), np.array(all_amps)

    @staticmethod
    def compute_svd(data_matrix):
        """
        Computes SVD of the data matrix.
        Args:
            data_matrix: (Channels, Time)
        Returns:
            U, S, VT
            U: (Channels, Channels) - Spatial Modes (columns)
            S: (Channels,) - Singular Values
            VT: (Time, Time) (if full_matrices=False, usually (K, Time))
        """
        if data_matrix is None:
            return None, None, None
            
        # SVD
        # Input: (Channels, Time)
        # U -> (Channels, K), S -> (K,), VT -> (K, Time)
        try:
            U, S, VT = np.linalg.svd(data_matrix, full_matrices=False)
            return U, S, VT
        except Exception as e:
            print(f"SVD Error: {e}")
            return None, None, None

    @staticmethod
    def compute_spatial_structure(spatial_mode, num_coils=12):
        """
        Computes the interpolated spatial structure curve.
        """
        _conf = _analysis_conf.get("spatial", {})
        radius = _conf.get("radius", 40)
        """
        Computes the interpolated spatial structure curve.
        
        Args:
            spatial_mode: 1D array of shape (num_coils,) representing weights.
            num_coils: Number of sensors.
            radius: Base radius.
            
        Returns:
            dict containing:
             'x_smooth', 'y_smooth': Interpolated curve
             'x_disp', 'y_disp': Displaced probe positions
             'x_orig', 'y_orig': Original probe positions
        """
        if len(spatial_mode) != num_coils:
            print(f"Spatial mode len {len(spatial_mode)} != num_coils {num_coils}")
            return None
            
        angles = np.linspace(0, 2 * np.pi, num_coils, endpoint=False)
        X = radius * np.cos(angles)
        Y = radius * np.sin(angles)
        
        # Normalize and Scale
        # spatial_mode = spatial_mode / np.max(np.abs(spatial_mode)) * 10
        # Check for zeros
        max_val = np.max(np.abs(spatial_mode))
        factor = _conf.get("factor", 15)
        if max_val > 0:
            mode_scaled = (spatial_mode / max_val) * factor
        else:
            mode_scaled = spatial_mode # All zeros
            
        X_disp = X + mode_scaled * np.cos(angles)
        Y_disp = Y + mode_scaled * np.sin(angles)
        
        # Close the loop for interpolation
        X_disp_closed = np.append(X_disp, X_disp[0])
        Y_disp_closed = np.append(Y_disp, Y_disp[0])
        
        try:
            interp_points = _conf.get("interp_points", 200)
            tck, u = splprep([X_disp_closed, Y_disp_closed], s=0, per=True)
            unew = np.linspace(0, 1.0, interp_points)
            x_smooth, y_smooth = splev(unew, tck)
            
            return {
                'x_smooth': x_smooth, 'y_smooth': y_smooth,
                'x_disp': X_disp, 'y_disp': Y_disp,
                'x_orig': X, 'y_orig': Y
            }
        except Exception as e:
            print(f"Spline Error: {e}")
            return None
