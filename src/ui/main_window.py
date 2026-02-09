# src/ui/main_window.py
import sys
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QLineEdit, QPushButton, QComboBox, QSplitter, QFrame, QTabWidget, QFileDialog)
from PySide6.QtCore import Qt
from src.ui.widgets.spectrogram_widget import SpectrogramWidget
from src.ui.widgets.wavelet_widget import WaveletWidget
from src.ui.widgets.phase_widget import PhaseWidget
from src.ui.widgets.phase_cycle_widget import PhaseCycleWidget
from src.ui.widgets.svd_widget import SVDWidget
from src.data.loader import fetch_mhd_data, load_mds_data, load_txt_data
from src.data.analysis import SignalProcessor
from src.utils.consts import MODE_POLOIDAL, MODE_TOROIDAL
import os
import numpy as np
# import json
from src.ui.dialogs.init_phase_dialog import InitPhaseDialog
from src.ui.dialogs.amplitude_multiplier_dialog import AmplitudeMultiplierDialog
from src.ui.dialogs.export_dialog import ExportDialog
from src.utils.export_manager import ExportManager
from src.utils.config_manager import config_manager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MHD Analysis Program")
        self.resize(1600, 800)

        # Main Layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # Data Storage
        self.current_data = None
        self.current_time = None
        self.current_fs = 200000.0
        self.last_loaded_shot = None
        self._updating_t0 = False
        
        # Load Params
        self.params_dict = config_manager.get_params()
        
        # Data Storage for t0 Shift
        self.original_data_matrix = None # Raw data reference
        self.original_time_array = None
        self.original_time_array = None
        self.original_time_array = None
        self.t0_offsets = {} # {channel_idx: offset_ms}
        self.amplitude_multipliers = {} # {channel_idx: multiplier_float}
        
        # Plasma Duration Range (for Spectrogram Reset)
        self.plasma_start_time = None
        self.plasma_end_time = None
        self.current_duration = 0.0
        self.current_ip_max = 0.0
        self.view_min = None
        self.view_max = None

        # UI Components
        self.setup_top_panel()
        self.setup_central_splitter()
        
        
        # Apply Theme
        self.apply_dark_theme()
        # dark_style = """
        # QMainWindow, QWidget {
        #     background-color: #000000;
        #     color: #dddddd;
        #     font-family: "Segoe UI", sans-serif;
        # }
        # QGraphicsView {
        #     border: 2px solid #2b2b2b; /* Visible gray border */
        #     border-radius: 4px;
        # }
        # """
        # self.setStyleSheet(dark_style)
        
    def apply_dark_theme(self):
        # Modern Dark Theme Palette
        # Background: #121212 (Deep Dark)
        # Surface: #1e1e1e (Card/Panel)
        # Accent: #007acc (Blue)
        # Text: #e0e0e0 (Off-white)
        # Borders: #333333
        
        dark_style = """
        QMainWindow, QWidget {
            background-color: #121212;
            color: #e0e0e0;
            font-family: "Segoe UI", sans-serif;
            font-size: 10pt;
        }
        
        /* --- Frames & Panels --- */
        QFrame {
            background-color: #1e1e1e;
            border: 1px solid #333333;
            border-radius: 6px;
        }
        QSplitter::handle {
            background-color: #333333;
            width: 2px;
        }
        
        /* --- Inputs --- */
        QLineEdit, QComboBox {
            background-color: #2d2d2d;
            color: #ffffff;
            border: 1px solid #3e3e3e;
            padding: 6px;
            border-radius: 4px;
            selection-background-color: #007acc;
        }
        QLineEdit:focus, QComboBox:focus {
            border: 1px solid #007acc;
            background-color: #333333;
        }
        QComboBox::drop-down {
            border: none;
            width: 20px;
        }
        QComboBox::down-arrow {
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid #e0e0e0;
            margin-right: 8px;
        }
        
        /* --- Buttons --- */
        QPushButton {
            background-color: #007acc;
            color: #ffffff;
            border: none;
            padding: 6px 16px;
            border-radius: 4px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #0062a3;
        }
        QPushButton:pressed {
            background-color: #004d80;
        }
        QPushButton:disabled {
            background-color: #333333;
            color: #888888;
        }
        
        /* --- Labels --- */
        QLabel {
            background-color: transparent;
            border: none;
            color: #cccccc;
        }
        
        /* --- Tabs --- */
        QTabWidget::pane {
            border: 1px solid #333333;
            background-color: #1e1e1e;
            border-radius: 6px;
            top: -1px; /* Overlap with tab bar */
        }
        QTabBar::tab {
            background-color: #252526;
            color: #cccccc;
            padding: 8px 20px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            border: 1px solid transparent;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background-color: #1e1e1e; /* Match pane */
            color: #ffffff;
            border-top: 2px solid #007acc; /* Accent top border */
            border-bottom: 2px solid #1e1e1e; /* Merge with pane */
        }
        QTabBar::tab:hover:!selected {
            background-color: #2d2d2d;
        }
        
        /* --- Plots --- */
        QGraphicsView {
            background-color: #000000;
            border: 1px solid #444444;
            border-radius: 6px;
        }
        """
        self.setStyleSheet(dark_style)
        
    def setup_top_panel(self):
        panel = QFrame()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(0, 5, 5, 5)
        # layout.setSpacing(8)
        
        # Shot No
        layout.addSpacing(10)
        layout.addWidget(QLabel("Shot No:"))
        self.shot_input = QLineEdit()
        self.shot_input.setFixedWidth(60)
        layout.addWidget(self.shot_input)
        
        # IP 
        layout.addWidget(QLabel("IP:"))
        self.ip_combo = QComboBox()
        self.ip_combo.setFixedWidth(55)
        self.ip_combo.addItems(["IP1", "IP2"])
        layout.addWidget(self.ip_combo)
        
        # Mode
        layout.addWidget(QLabel("Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.setFixedWidth(70)
        self.mode_combo.addItems([MODE_POLOIDAL, MODE_TOROIDAL])
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        layout.addWidget(self.mode_combo)
        
        # Channel
        layout.addWidget(QLabel("Channel:"))
        self.channel_combo = QComboBox()
        self.channel_combo.setFixedWidth(70)
        self.channel_combo.currentIndexChanged.connect(self.on_channel_changed)
        layout.addWidget(self.channel_combo)
        
        # Type
        layout.addWidget(QLabel("Type:"))
        self.type_combo = QComboBox()
        self.type_combo.setFixedWidth(50)
        self.type_combo.addItems(["T", "N"])
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        layout.addWidget(self.type_combo)
        
        # Init list
        self.update_channel_list(self.mode_combo.currentText())

        # Spacer before Method
        layout.addSpacing(15)

        # Method Selection
        layout.addWidget(QLabel("Method:"))
        self.method_combo = QComboBox()
        self.method_combo.addItems(["DAQ SV.", "Text file"])
        self.method_combo.currentTextChanged.connect(self.on_method_changed)
        layout.addWidget(self.method_combo)

        # Path Selection
        self.path_input = QLineEdit(r"example/1275")
        self.path_input.setFixedWidth(300)
        self.path_input.setPlaceholderText("Data Path")
        self.path_input.setToolTip("Path to data files")
        layout.addWidget(self.path_input)

        self.browse_btn = QPushButton("Browse")
        # self.browse_btn.setFixedWidth(60)
        self.browse_btn.clicked.connect(self.on_browse_clicked)
        layout.addWidget(self.browse_btn)
        
        # Spacer before Load
        layout.addSpacing(5)

        # Load Button
        self.load_btn = QPushButton("Load")
        self.load_btn.clicked.connect(self.on_load_clicked)
        layout.addWidget(self.load_btn)
        
        # Set t0 Button
        self.btn_set_t0 = QPushButton("Init Phase")
        self.btn_set_t0.clicked.connect(self.on_set_t0_clicked)
        layout.addWidget(self.btn_set_t0)

        # Amplitude Multiplier Button
        self.btn_amp_mult = QPushButton("Amp. Signal")
        self.btn_amp_mult.clicked.connect(self.on_set_amplitude_clicked)
        layout.addWidget(self.btn_amp_mult)

        # Export Button
        self.btn_export = QPushButton("Export")
        self.btn_export.clicked.connect(self.on_export_clicked)
        self.btn_export.setStyleSheet("""
            QPushButton {
                background-color: #d17519; 
                color: white;
                border: none;
                padding: 6px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #b05e10; /* Darker Orange for hover effect */
            }
            QPushButton:pressed {
                background-color: #8a4a0c; /* Even darker for click effect */
            }
        """)
        layout.addWidget(self.btn_export)
        
        # Spacer after buttons
        
        # Spacer after Set t0
        layout.addSpacing(20)
        
        # Info
        self.duration_label = QLabel("Duration(ms): N/A   ")
        layout.addWidget(self.duration_label)
        
        self.ip_max_label = QLabel("Current(kA): N/A   ")
        layout.addWidget(self.ip_max_label)
        
        # Final stretch
        layout.addStretch()

        self.main_layout.addWidget(panel)
        
        # Init State
        self.on_method_changed(self.method_combo.currentText())
    
    def create_channel_names(self, num_channels):
        mode_str = self.mode_combo.currentText()
        if mode_str == MODE_POLOIDAL: # 'm'
            channel_names = [f"OBP{i}" for i in range(1, 13)]
        else: # 'n'
            channel_names = [f"M{i}" for i in range(1, 15)]
            
        if len(channel_names) != num_channels:
            channel_names = [f"CH{i+1}" for i in range(num_channels)]
            
    

    def on_method_changed(self, text):
        is_text_file = (text == "Text file")
        self.path_input.setEnabled(is_text_file)
        self.browse_btn.setEnabled(is_text_file)

    def setup_central_splitter(self):
        splitter = QSplitter(Qt.Horizontal)
        
        # Left Panel: Spectrogram & Wavelet
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        
        self.spectro_widget = SpectrogramWidget()
        self.spectro_widget.region_changed.connect(self.on_spectro_region_changed)
        self.spectro_widget.request_overlay_load.connect(self.load_spectrogram_overlay)
        left_layout.addWidget(self.spectro_widget, stretch=1)
        
        # Keep WaveletWidget for visualization only (no interaction needed for Phase anymore)
        self.wavelet_widget = WaveletWidget()
        # Connection moved to end of method
        # self.wavelet_widget.time_point_selected.connect(self.on_wavelet_point_selected) # Removed
        left_layout.addWidget(self.wavelet_widget, stretch=1)
        
        splitter.addWidget(left_widget)
        
        # Right Panel: Phase
        # Panel 3
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        self.tabs = QTabWidget()
        right_layout.addWidget(self.tabs)
        
        # Tab 1: Phase Difference
        self.phase_widget = PhaseWidget()
        self.tabs.addTab(self.phase_widget, "Phase Difference")
        
        # Tab 2: Phase Cycle
        self.phase_cycle_widget = PhaseCycleWidget()
        self.tabs.addTab(self.phase_cycle_widget, "Phase Cycle")
        
        # Tab 3: SVD Technique
        self.svd_widget = SVDWidget()
        self.tabs.addTab(self.svd_widget, "SVD technique")
        
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        
        # Connect Signals (Now that all widgets exist)
        # Link GuideManagers
        self.wavelet_widget.guide_manager.guide_updated.connect(lambda *a: self.sync_guide(self.wavelet_widget, *a))
        self.phase_widget.guide_manager.guide_updated.connect(lambda *a: self.sync_guide(self.phase_widget, *a))
        self.phase_cycle_widget.guide_manager.guide_updated.connect(lambda *a: self.sync_guide(self.phase_cycle_widget, *a))
        
        self.wavelet_widget.guide_manager.guide_cleared.connect(lambda: self.sync_guide_clear(self.wavelet_widget))
        self.phase_widget.guide_manager.guide_cleared.connect(lambda: self.sync_guide_clear(self.phase_widget))
        self.phase_cycle_widget.guide_manager.guide_cleared.connect(lambda: self.sync_guide_clear(self.phase_cycle_widget))
        
        # Link Zoom States
        self.phase_widget.view_zoom_changed.connect(self.phase_cycle_widget.set_zoom_state)
        self.phase_cycle_widget.view_zoom_changed.connect(self.phase_widget.set_zoom_state)
        
        self.main_layout.addWidget(splitter)
        
        # Populate Spectrogram Widget Options (After creation)
        if hasattr(self, 'spectro_widget') and self.params_dict:
            self.spectro_widget.set_param_options(list(self.params_dict.keys()))
        
    def sync_guide(self, source_widget, t1, c1, t2, c2, slope, velocity):
        """Propagate guide line to other widgets"""
        widgets = [self.wavelet_widget, self.phase_widget, self.phase_cycle_widget]
        
        for w in widgets:
            if w != source_widget:
                if hasattr(w, 'guide_manager'):
                    w.guide_manager.set_guide_line(t1, c1, t2, c2, slope, velocity)

    def sync_guide_clear(self, source_widget):
        """Propagate guide clear to other widgets"""
        widgets = [self.wavelet_widget, self.phase_widget, self.phase_cycle_widget]
        
        for w in widgets:
            if w != source_widget:
                if hasattr(w, 'guide_manager'):
                    w.guide_manager.clear_guide()

    def get_channel_names(self, mode_str, num_channels=None):
        """Generate channel names based on mode and channel count."""
        if mode_str == MODE_POLOIDAL: # 'm'
            channel_names = [f"OBP{i}" for i in range(1, 13)] # 1..12
        else: # 'n'
            channel_names = [f"M{i}" for i in range(1, 15)] # 1..14
            
        if num_channels is not None and len(channel_names) != num_channels:
            channel_names = [f"CH{i+1}" for i in range(num_channels)]
            
        return channel_names
        
    def update_channel_list(self, mode_str):
        self.channel_combo.blockSignals(True)
        self.channel_combo.clear()
        
        items = self.get_channel_names(mode_str)
        self.channel_combo.addItems(items)
        self.channel_combo.blockSignals(False)

    def on_mode_changed(self, mode_str):
        self.update_channel_list(mode_str)
        
        # Auto-set Wavelet Range
        if mode_str == MODE_POLOIDAL: # 'm'
            self.wavelet_widget.plot_widget.setYRange(0.5, 12.5, padding=0)
        else: # 'n'
            self.wavelet_widget.plot_widget.setYRange(0.5, 14.5, padding=0)
            
        # Update Bottom Widgets Mode
        if hasattr(self, 'phase_widget'):
            self.phase_widget.set_mode(mode_str)
            
        if hasattr(self, 'phase_cycle_widget'):
            self.phase_cycle_widget.set_mode(mode_str)
            
        if hasattr(self, 'svd_widget'):
            self.svd_widget.set_mode(mode_str)
            
        if self.last_loaded_shot is not None:
            self.on_load_clicked()

    def on_type_changed(self, type_str):
        if self.last_loaded_shot is not None:
            self.on_load_clicked()

    def on_channel_changed(self, index, keep_view=True):
        if self.current_data is None or index < 0:
            return
            
        # Update Spectrogram with selected channel
        if index < self.current_data.shape[0]:
            t_offset_sec = self.current_time[0]
            self.spectro_widget.set_data(self.current_data[index, :], self.current_fs, t_offset=t_offset_sec, keep_view=keep_view)
            
            # Restore the "reset target" (Plasma Duration) if we have it
            if self.view_min is not None and self.view_max is not None:
                self.spectro_widget.set_default_view_range(self.view_min, self.view_max, update_plot=False)

    def on_browse_clicked(self):
        start_dir = self.path_input.text()
        if not os.path.isdir(start_dir):
            start_dir = os.getcwd() # Fallback
            
        dir_path = QFileDialog.getExistingDirectory(self, "Select Data Directory", start_dir)
        if dir_path:
            self.path_input.setText(dir_path)
            
            # Auto-Extract Shot Number from Folder Name
            folder_name = os.path.basename(dir_path)
            if folder_name.isdigit():
                self.shot_input.setText(folder_name)

    def on_load_clicked(self):
        shot_no = self.shot_input.text()
        mode_str = self.mode_combo.currentText()
        type_str = self.type_combo.currentText()
        ip_choice = self.ip_combo.currentText()
        method = self.method_combo.currentText()
        
        try:
            shot_int = int(shot_no)
        except ValueError:
            return

        self.load_btn.setEnabled(False)
        self.load_btn.setText("Loading...")
        
        # Check if we should keep view (same shot)
        # Note: self.last_loaded_shot is updated at the END of this function (on success)
        keep_view = (self.last_loaded_shot == shot_int)
        
        # Set Flag for WaveletWidget Logic in on_spectro_region_changed
        self._loading_new_shot = not keep_view 
        
        # Fetch Data
        base_path = None
        if method == "Text file":
            base_path = self.path_input.text()
        
        # If DAQ SV, base_path stays None, loader uses default.
        
        data, time, ip_data, ip_time = fetch_mhd_data(shot_int, method, mode_str, suffix=type_str, ip_signal=ip_choice, base_path=base_path)
        
        if data is None:
            self.load_btn.setText("Failed")
            self.load_btn.setEnabled(True)
            self._loading_new_shot = False # Reset Flag
            return

        # Store Original Data for t0 Shift
        self.original_data_matrix = data
        self.original_time_array = time
        self.t0_offsets = {} # Reset
        self.amplitude_multipliers = {} # Reset

        
        # Apply Logic (Populates self.current_data)
        self.apply_t0_corrections(update_ui=False)
        self.current_time = time
        
        self.current_fs = 200000.0 # Assuming fixed or returned from loader? Hardcoded for now.
        
        # self.duration_label.setText(f"Duration: {duration:.2f} ms") 
        duration, ip_max, start_idx = SignalProcessor.cal_duration(ip_data, ip_time) if ip_data is not None else (0,0,0)
        
        self.current_duration = duration
        self.current_ip_max = ip_max / 1000.0 if ip_max else 0.0
        
        self.duration_label.setText(f"Duration(ms): {duration:.2f}   ") 
        self.ip_max_label.setText(f"Current(kA): {ip_max/1000:.2f}   ")

        # Update Spectrogram & IP Overlay
        # Use currently selected channel
        self.current_data = data
        self.current_time = time
        
        # Pass IP data to Spectrogram
        # self.spectro_widget.set_ip_data(ip_time, ip_data) # Disabled auto-load as requested

        # Check if we should keep view (same shot)
        # keep_view = (self.last_loaded_shot == shot_int) # Already calculated above
        self.last_loaded_shot = shot_int

        # Update Phase Widget Context
        self.phase_widget.set_context(self.current_data, self.current_time, fs=self.current_fs, reset=not keep_view)
        if hasattr(self, 'phase_cycle_widget'):
            self.phase_cycle_widget.set_context(self.current_data, self.current_time, fs=self.current_fs, reset=not keep_view)
        
        if hasattr(self, 'svd_widget'):
            self.svd_widget.set_context(self.current_data, self.current_time, fs=self.current_fs)
        
        # Trigger channel update (will set spectrogram data)
        self.on_channel_changed(self.channel_combo.currentIndex(), keep_view=keep_view)
        
        
        # Auto-Crop Range (Zoom to activity) - Only if NOT keeping view
        if duration > 0 and ip_time is not None:
            # ip_time is usually same basis as time? 
            # cal_duration uses ip_time.
            # start_idx is index in ip_data.
            
            t_start = ip_time[start_idx]
            t_end = t_start + duration
            
            # Store for future channel changes / resets
            self.plasma_start_time = t_start
            self.plasma_end_time = t_end
            
            # t_start = ip_time[start_idx]
            # t_end = t_start + duration
            
            # User request: exact duration, no padding
            self.view_min = t_start - duration*0.1
            self.view_max = t_end + duration*0.1
            
            # Apply to Spectrogram Plot
            # If keeping view, update the target but don't zoom.
            # If NOT keeping view, update target AND zoom.
            update_plot = not keep_view
            self.spectro_widget.set_default_view_range(self.view_min, self.view_max, update_plot=update_plot)
            
            if not keep_view:
                # Set ROI (Gap) to start at active time with 10ms width
                self.spectro_widget.time_roi.setRegion([t_start, t_start + 5])
        else:
             # Reset stored duration if load failed to find plasma
             self.plasma_start_time = None
             self.plasma_end_time = None



        self.load_btn.setText("Load")
        self.load_btn.setEnabled(True)
        self._loading_new_shot = False # Reset Flag

    def on_spectro_region_changed(self, t_start, t_end, freq_center, dfreq):
        if self.current_data is None:
            return
            
        # Update SVD params if available
        # if hasattr(self, 'svd_widget'):
        #     self.svd_widget.update_params(t_start, t_end, freq_center, dfreq)
            
        # # Update Phase Cycle params if available
        # if hasattr(self, 'phase_cycle_widget'):
        #     # Assuming PhaseCycleWidget also needs update?
        #     # User didn't explicitly say so, but likely for the Wavelet calc inside it.
        #     # But currently PhaseCycleWidget has its own calc button.
        #     pass
            
        
        sliced_time, filtered_data = SignalProcessor.compute_wavelet_data(
            self.current_data, self.current_time, t_start, t_end, freq_center, dfreq, fs=self.current_fs
        )
        
        # keep_view = getattr(self, '_updating_t0', False)
        keep_view = not getattr(self, '_loading_new_shot', False)
        
        # Pass t_start explicitly as anchor
        self.wavelet_widget.update_plot(sliced_time, filtered_data, keep_view=keep_view)
        
        # Update Phase Widget Parameters (Right Panel)
        self.phase_widget.update_params(t_start, t_end, freq_center, dfreq, keep_view=keep_view)
        if hasattr(self, 'phase_cycle_widget'):
            self.phase_cycle_widget.update_params(t_start, t_end, freq_center, dfreq, keep_view=keep_view)
        self.svd_widget.update_params(t_start, t_end, freq_center, dfreq)

    def load_spectrogram_overlay(self, param_name):
        shot_no = self.shot_input.text()
        method = self.method_combo.currentText()
        
        try:
            shot_int = int(shot_no)
        except ValueError:
            return

        base_path = None
        if method == "Text file":
            base_path = self.path_input.text()

        param_name = param_name.strip()
        
        # print(f"Loading overlay param: {param_name}")
        
        if method == "Text file":
            results = load_txt_data(shot_int, [param_name], base_path=base_path)
        else: # DAQ
            results = load_mds_data(shot_int, [param_name])
            
        if results and param_name in results:
            data, time = results[param_name]
            if data is not None and time is not None:
                # Get Unit
                unit = ""
                if param_name in self.params_dict:
                    unit = self.params_dict[param_name].get("unit", "")
                
                label = f"{param_name}"
                self.spectro_widget.set_overlay_data(time, data, label=label, units=unit)
            else:
                print(f"Failed to load data for {param_name}")
        else:
            print(f"Failed to fetch {param_name}")

    def on_set_t0_clicked(self):
        """Open Init Phase Dialog"""
        if self.original_data_matrix is None:
            # No data loaded
            print("No data loaded")
            return
            
        num_channels = self.original_data_matrix.shape[0]
        
        # Get Channel Names
        # Get Channel Names
        mode_str = self.mode_combo.currentText()
        channel_names = self.get_channel_names(mode_str, num_channels)
            
        # Store state before dialog for revert
        self.pre_dialog_offsets = self.t0_offsets.copy()
        
        # --- Store Lock State & Force Unlock ---
        phase_locked = False
        if hasattr(self.phase_widget, 'lock_check'):
            phase_locked = self.phase_widget.lock_check.isChecked()
            self.phase_widget.lock_check.setChecked(False)
            
        cycle_locked = False
        if hasattr(self.phase_cycle_widget, 'lock_check'):
            cycle_locked = self.phase_cycle_widget.lock_check.isChecked()
            self.phase_cycle_widget.lock_check.setChecked(False)
        # ---------------------------------------
        
        dialog = InitPhaseDialog(channel_names, self.type_combo.currentText(),self.t0_offsets, self)
        dialog.t0_changed.connect(self.live_update_t0)
        
        if dialog.exec():
            # Accepted - Keep changes
            self.t0_offsets = dialog.current_offsets
            self.apply_t0_corrections()
        else:
            # Cancelled - Revert to PRE-DIALOG state
            # Crucial because live_update_t0 modified t0_offsets during the dialog
            self.t0_offsets = self.pre_dialog_offsets
            self.apply_t0_corrections()
            
        # --- Restore Lock State ---
        if hasattr(self.phase_widget, 'lock_check'):
            self.phase_widget.lock_check.setChecked(phase_locked)
            
        if hasattr(self.phase_cycle_widget, 'lock_check'):
             self.phase_cycle_widget.lock_check.setChecked(cycle_locked)
        # -------------------------- 

    def on_export_clicked(self):
        """Handle Export Dialog"""
        if self.current_data is None:
            # Maybe show warning? Or allow partial export?
            pass
            
        shot_no = self.shot_input.text()
        mode_str = self.mode_combo.currentText()
        type_str = self.type_combo.currentText()
        
        dialog = ExportDialog(shot_no, mode_str, type_str, self)
        if dialog.exec():
            config = dialog.selected_options
            
            # Prepare Widget Map
            # Prepare Widgets Map with Tuples (Grab Source, Metadata Source)
            widgets_map = {
                'spectrogram': (self.spectro_widget.plot_widget, self.spectro_widget),
                'wavelet': (self.wavelet_widget.plot_widget, self.wavelet_widget),
                'wavelet_peaks_phase_diff': (self.phase_widget.peaks_plot, self.phase_widget),
                'phase_diff_coil': (self.phase_widget.fit_plot, self.phase_widget),
                'wavelet_peaks_phase_cycle': (self.phase_cycle_widget.peaks_plot, self.phase_cycle_widget),
                'phase_cycle': (self.phase_cycle_widget.cycle_plot if hasattr(self.phase_cycle_widget, 'cycle_plot') else None, self.phase_cycle_widget),
                'singular_values': (self.svd_widget.sv_plot, self.svd_widget),
                'spatial_structure': (self.spatial_plot if hasattr(self, 'spatial_plot') else self.svd_widget.spatial_plot, self.svd_widget),
                 # Tables (Virtual items, handled by data)
                'init_phase_table': None,
                'amp_signal_table': None
            }
            
            # Prepare Context
            context = {
                'shot': shot_no,
                'mode': mode_str,
                'type': type_str,
                'duration': getattr(self, 'current_duration', 0.0),
                'ip_max': getattr(self, 'current_ip_max', 0.0),
                'init_phase_table': self.t0_offsets,
                'amp_signal_table': self.amplitude_multipliers
            }
            
            # Execute Export
            try:
                ExportManager.export(config, widgets_map, context)
            except Exception as e:
                print(f"Export Error: {e}") 
                import traceback
                traceback.print_exc() 

    def on_set_amplitude_clicked(self):
        """Open Amplitude Multiplier Dialog"""
        if self.original_data_matrix is None:
            return
            
        num_channels = self.original_data_matrix.shape[0]
        
        # Reuse logic for channel names
        # Reuse logic for channel names
        mode_str = self.mode_combo.currentText()
        channel_names = self.get_channel_names(mode_str, num_channels)
            
        # Store state before dialog
        self.pre_dialog_multipliers = self.amplitude_multipliers.copy()
        
        dialog = AmplitudeMultiplierDialog(channel_names, self.type_combo.currentText(), self.amplitude_multipliers, self)
        dialog.amplitude_changed.connect(self.live_update_amplitude)
        
        if dialog.exec():
            self.amplitude_multipliers = dialog.current_multipliers
            self.apply_t0_corrections()
        else:
            self.amplitude_multipliers = self.pre_dialog_multipliers
            self.apply_t0_corrections()

    def live_update_amplitude(self, multipliers):
        self.amplitude_multipliers = multipliers
        self.apply_t0_corrections() 
            
    def live_update_t0(self, offsets):
        """Called when slider moves in dialog"""
        # print(f"DEBUG: live_update_t0 called with {offsets}")
        self.t0_offsets = offsets
        self.apply_t0_corrections()
        
    def apply_t0_corrections(self, update_ui=True):
        """Apply t0 shifts to original data to create active data"""
        if self.original_data_matrix is None:
            return

        fs = self.current_fs
        
        # Start from original
        self.current_data = self.original_data_matrix.copy()
        # Time array remains same? Yes, we shift data relative to time.
        
        num_channels = self.current_data.shape[0]
        num_samples = self.current_data.shape[1]
        
        for i in range(num_channels):
            t0 = self.t0_offsets.get(i, 0.0)
            if t0 == 0:
                continue
            
            # t0 ms -> shift samples
            # t0 positive (delayed sign) -> shift left (negative) to fix?
            # User requirement: "init phase (t0) -10 to +10 ms"
            # If t0 is the delay, we subtract it. shift = -t0.
            
            shift_samples = int(-1 * t0 * fs / 1000.0)
            if shift_samples == 0:
                continue
                
            row_data = self.original_data_matrix[i]
            new_row = np.zeros_like(row_data)
            
            if shift_samples > 0:
                 # Shift Right
                 if shift_samples < num_samples:
                    new_row[shift_samples:] = row_data[:-shift_samples]
            else:
                # Shift Left
                abs_shift = abs(shift_samples)
                if abs_shift < num_samples:
                    new_row[:-abs_shift] = row_data[abs_shift:]
                    
            self.current_data[i] = new_row
        
        # Apply Amplitude Multipliers
        for i in range(num_channels):
            mult = self.amplitude_multipliers.get(i, 1.0)
            if mult != 1.0:
                self.current_data[i] = self.current_data[i] * mult
            
        if update_ui:
            self._updating_t0 = True
            try:
                # Trigger UI updates
                # We need to refresh all widgets with new data
                # Use logic similar to on_channel_changed or on_data_loaded end part
                
                # Update Phase Widget Context
                self.phase_widget.set_context(self.current_data, self.current_time, self.current_fs, reset=False)
                self.phase_cycle_widget.set_context(self.current_data, self.current_time, self.current_fs, reset=False)
                self.svd_widget.set_context(self.current_data, self.current_time, self.current_fs, reset=False)
                
                # Refresh Calculations if active
                if hasattr(self.phase_widget, 'refresh'):
                    self.phase_widget.refresh(keep_view=True)
                if hasattr(self.phase_cycle_widget, 'refresh'):
                    self.phase_cycle_widget.refresh(keep_view=True)
                if hasattr(self.svd_widget, 'refresh'):
                    self.svd_widget.refresh()
                
                # Update Spectrogram (Current Channel)
                self.on_channel_changed(self.channel_combo.currentIndex(), keep_view=True)
            finally:
                self._updating_t0 = False
