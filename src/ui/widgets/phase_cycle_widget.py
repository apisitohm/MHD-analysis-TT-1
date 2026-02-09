# src/ui/widgets/phase_cycle_widget.py
import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QPushButton, QSplitter, QCheckBox)
from PySide6.QtCore import Qt, Signal
from src.data.analysis import SignalProcessor

from src.ui.widgets.guide_manager import GuideManager

class PhaseCycleWidget(QWidget):
    # Signals
    view_zoom_changed = Signal(float, float) # offset, width

    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0,0,0,0)
        
        # Splitter for 2 Rows
        self.splitter = QSplitter(Qt.Vertical)
        self.layout.addWidget(self.splitter)
        
        # --- Top Row: Wavelet Peaks ---
        self.top_widget = QWidget()
        self.top_layout = QVBoxLayout(self.top_widget)
        self.top_layout.setContentsMargins(0,5,0,0)
        
        # Controls for Top Row
        self.controls_layout = QHBoxLayout()
        self.controls_layout.addSpacing(5)
        self.calc_btn = QPushButton("Enable Wavelet Peaks")
        self.calc_btn.setFixedWidth(180)
        self.calc_btn.setCheckable(True)
        self.calc_btn.clicked.connect(self.on_calc_toggled)
        self.controls_layout.addWidget(self.calc_btn)
        self.info_label = QLabel("Drag vertical line")
        self.controls_layout.addWidget(self.info_label)
        
        self.lock_check = QCheckBox("Lock Result")
        self.controls_layout.addWidget(self.lock_check)
        
        # Create Plot first
        self.peaks_plot = pg.PlotWidget()
        self.peaks_plot.setTitle(f"Wavelet Peaks at Time = N/A ms", color="w", size="12pt")
        self.peaks_plot.setLabel('left', 'Channel')
        self.peaks_plot.plotItem.getAxis('left').setPen(pg.mkPen('#ffffff', width=1))
        self.peaks_plot.plotItem.getAxis('left').setTextPen(pg.mkPen('#ffffff', width=1))
        self.peaks_plot.setLabel('bottom', 'Time', units='ms')
        self.peaks_plot.plotItem.getAxis('bottom').setPen(pg.mkPen('#ffffff', width=1))
        self.peaks_plot.plotItem.getAxis('bottom').setTextPen(pg.mkPen('#ffffff', width=1))
        
        self.peaks_plot.getPlotItem().setContentsMargins(10, 10, 20, 20)
        # self.peaks_plot.getViewBox().setMouseMode(pg.ViewBox.RectMode)
        # self.peaks_plot.getPlotItem().setContentsMargins(10, 10, 20, 20)
        
        # Guide Manager
        self.guide_manager = GuideManager(self.peaks_plot)

        
        # Connect click? PhaseCycle didn't have click handling before (dragging line only).
        # We need to add click handling for GuideManager.
        self.peaks_plot.scene().sigMouseClicked.connect(self.on_plot_clicked)
        self.peaks_plot.sigRangeChanged.connect(self.on_view_range_changed)
        
        self.controls_layout.addStretch()
        self.top_layout.addLayout(self.controls_layout)
        
        self.top_layout.addWidget(self.peaks_plot)
        
        self.peaks_scatter = pg.ScatterPlotItem(size=10, pen=pg.mkPen(None), brush=pg.mkBrush(255, 255, 0, 200)) 
        self.peaks_plot.addItem(self.peaks_scatter)
        
        # Infinite Line
        self.v_line = pg.InfiniteLine(angle=90, movable=True)
        self.v_line.setPen(pg.mkPen((0, 255, 0, 200), width=1))
        self.v_line.setHoverPen(pg.mkPen((0, 255, 0, 255), width=4)) # Slightly brighter/thicker on hover
        self.v_line.sigPositionChanged.connect(self.on_vline_moved)
        self.peaks_plot.addItem(self.v_line)
        # self.peaks_plot.getPlotItem().setContentsMargins(10, 10, 20, 20)
        
        self.splitter.addWidget(self.top_widget)
        
        # --- Bottom Row: Phase Fit ---
        self.bottom_widget = QWidget()
        self.bottom_layout = QVBoxLayout(self.bottom_widget)
        self.bottom_layout.setContentsMargins(0,0,0,0)
        
        self.cycle_plot = pg.PlotWidget()
        self.cycle_plot.setTitle(f"Phase Differences at Time = N/A ms", color="w", size="12pt")
        self.cycle_plot.setLabel('left', 'Phase Difference', units='degree')
        self.cycle_plot.plotItem.getAxis('left').setPen(pg.mkPen('#ffffff', width=1))
        self.cycle_plot.plotItem.getAxis('left').setTextPen(pg.mkPen('#ffffff', width=1))
        self.cycle_plot.setLabel('bottom', 'Mirnov coils')
        self.cycle_plot.plotItem.getAxis('bottom').setPen(pg.mkPen('#ffffff', width=1))
        self.cycle_plot.plotItem.getAxis('bottom').setTextPen(pg.mkPen('#ffffff', width=1))
        self.cycle_plot.showGrid(x=True, y=True, alpha=0.3)
        self.cycle_plot.getPlotItem().setContentsMargins(10, 10, 20, 20)
        self.bottom_layout.addWidget(self.cycle_plot)
        
        self.splitter.addWidget(self.bottom_widget)
        
        # State
        self.current_data = None
        self.current_time = None
        self.current_t_start = 0
        self.current_t_end = 0
        self.current_freq = 0
        self.current_dfreq = 3000.0
        self.current_mode = 'm'
        
        self.filtered_data_T = None # (Time, Channels)
        self.sliced_time = None
        self.peaks_data = []

        # ROI Tracking
        self.current_x_offset = 0
        self.current_x_gap = None
        self._updating = False
        if self.current_mode == 'm':
            self.peaks_plot.setYRange(0.5, 12.5, padding=0) 
        else:
            self.peaks_plot.setYRange(0.5, 14.5, padding=0)
        self.peaks_plot.setXRange(0, 1)
        
    def set_mode(self, mode):
        self.current_mode = mode
        if mode == 'm':
            self.peaks_plot.setYRange(0.5, 12.5, padding=0)
        else:
            self.peaks_plot.setYRange(0.5, 14.5, padding=0)

    def set_context(self, data, time, fs=200000.0, reset=True):
        """Sets the raw data context."""
        self.current_data = data
        self.current_time = time
        self.current_fs = fs
        
        # Clear data dependants
        self.peaks_data = []
        self.filtered_data_T = None
        self.sliced_time = None
        
        if reset:
            self.peaks_scatter.setData([])
            self.calc_btn.setChecked(False)
            self.calc_btn.setText("Enable Wavelet Peaks")
            self.lock_check.setChecked(False)
            self.cycle_plot.clear()
            self.peaks_plot.setTitle(f"Wavelet Peaks at Time = N/A ms", color="w", size="12pt")
            self.cycle_plot.setTitle(f"Phase Differences at Time = N/A ms", color="w", size="12pt")
            
            # Reset Zoom Tracking
            self.current_x_offset = 0
            self.current_x_gap = None

    def update_params(self, t_start, t_end, freq, dfreq=3000.0, keep_view=False):
        """Updates parameters from Spectrogram/Controls."""
        
        # Cache current zoom state
        saved_offset = self.current_x_offset
        saved_gap = self.current_x_gap
        
        # Check if ROI Width changed (Resize vs Pan)
        prev_width = self.current_t_end - self.current_t_start
        new_width = t_end - t_start
        
        width_changed = abs(new_width - prev_width) > 1e-2
        
        self.current_t_start = t_start
        self.current_t_end = t_end
        self.current_freq = freq
        self.current_dfreq = dfreq
        
        # Force view reset ONLY if width changed (Resize)
        if width_changed:
            keep_view = False
            saved_offset = 0
            saved_gap = None
            self.current_x_offset = 0
            self.current_x_gap = None
        
        if self.calc_btn.isChecked():
            self.calculate_peaks(keep_view=keep_view)
            
            if saved_gap is not None:
                # Explicitly zoom using stored gaps
                self.zoom_to_range(t_start, saved_offset, saved_gap)
            
    def on_calc_toggled(self):
        if self.calc_btn.isChecked():
            self.calc_btn.setText("Disable Wavelet Peaks")
            
            # Smart Enable: Check if we have a shared zoom state to apply
            x_gap = getattr(self, 'current_x_gap', None)
            if x_gap is not None:
                # Calculate with keep_view=True so it doesn't auto-reset to full range
                self.calculate_peaks(keep_view=True)
                # Apply the specific zoom
                self.zoom_to_range(self.current_t_start, self.current_x_offset, self.current_x_gap)
            else:
                self.calculate_peaks(keep_view=False)
        else:
            self.calc_btn.setText("Enable Wavelet Peaks")
            self.peaks_scatter.setData([])
            self.filtered_data_T = None
            
    def refresh(self, keep_view=False):
        """Refreshes the plot calculation."""
        if self.calc_btn.isChecked():
            self.calculate_peaks(keep_view=keep_view)

    def calculate_peaks(self, keep_view=False):
        if self.current_data is None:
            return
            
        # 1. Filter Data (Wavelet/Bandpass)
        sliced_time, filtered_data_T = SignalProcessor.compute_wavelet_data(
            self.current_data, self.current_time, 
            self.current_t_start, self.current_t_end, 
            self.current_freq, self.current_dfreq, 
            fs=self.current_fs
        )
        
        if sliced_time is None:
            return
            
        self.sliced_time = sliced_time
        self.filtered_data_T = filtered_data_T
            
        # filtered_data_T is (Time, Channels). Need (Channels, Time) for peak finding per ch
        filtered_data = filtered_data_T.T 
        
        # 2. Find Peaks
        dist = int((1.0 / (self.current_freq + 1e-9)) * self.current_fs * 0.5)
        dist = max(1, dist)
        
        peaks = SignalProcessor.find_all_peaks(sliced_time, filtered_data, distance=dist)
        self.peaks_data = peaks
        
        # 3. Plot Peaks
        x = [p['t'] for p in peaks]
        y = [p['ch'] for p in peaks]
        self.peaks_scatter.setData(x, y)
        
        # Determine Data Range (ROI)
        self.x_range = (self.current_t_start, self.current_t_end)
        self.y_range = (0.5, 12.5 if self.current_mode == 'm' else 14.5)
        
        # Autozoom or Restore Offset
        # keep_view logic in update_params
        if not keep_view:
            self.peaks_plot.setXRange(self.current_t_start, self.current_t_end)
            if self.current_mode == 'm':
                self.peaks_plot.setYRange(0.5, 12.5, padding=0) # 12 channels (or 14 for n mode)
            else:
                self.peaks_plot.setYRange(0.5, 14.5, padding=0)
        
        
        # Init VLine to center (Follow ROI if not locked)
        if not self.lock_check.isChecked():
            center = (self.current_t_start + self.current_t_end) / 2
            self.v_line.setValue(center)
        
        # Trigger initial update based on current VLine position
        if not self.lock_check.isChecked():
            self.on_vline_moved()

    
    def zoom_to_range(self, spec_start, start_gap, zoom_width):
        self._updating = True
        try:
            self.peaks_plot.setXRange(spec_start + start_gap, spec_start + start_gap + zoom_width, padding=0)
            if self.current_mode == 'm':
                self.peaks_plot.setYRange(0.5, 12.5, padding=0) # 12 channels (or 14 for n mode)
            else:
                self.peaks_plot.setYRange(0.5, 14.5, padding=0)
        finally:
            self._updating = False

    def on_view_range_changed(self, _, ranges):
        if self._updating:
            return
            
        # ranges is [[xmin, xmax], [ymin, ymax]]
        xmin, xmax = ranges[0]
        # ymin, ymax = ranges[1] # Not used for now
        
        if hasattr(self, 'x_range') and self.x_range:
            spec_start = self.x_range[0]
            # spec_end = self.x_range[1]
            
            # Sync Logic: Track offsets relative to Spectrogram Start
            self.current_x_offset = xmin - spec_start
            self.current_x_gap = xmax - xmin
            
            # Emit Signal
            self.view_zoom_changed.emit(self.current_x_offset, self.current_x_gap)

    def set_zoom_state(self, offset, width):
        self.current_x_offset = offset
        self.current_x_gap = width
        
        # Apply immediately if possible
        if self.isVisible() and self.current_t_start != 0:
             self.zoom_to_range(self.current_t_start, offset, width)

    def on_vline_moved(self):
        if self.filtered_data_T is None or self.sliced_time is None:
            return
            
        t_ref = self.v_line.value()
        
        # Logic from user:
        # idx = np.where(data_time >= t_ref+0.0001)[0][0]
        # data_time -> self.sliced_time
        
        indices = np.where(self.sliced_time >= t_ref + 0.0001)[0]
        if len(indices) == 0:
            return
        idx = indices[0]
        
        if idx >= len(self.filtered_data_T):
            return
            
        # Data Matrix: (Time, Channels)
        data_signal = self.filtered_data_T
        
        # ref_signal = data_signal[:, 0]
        # Note: data_signal[:, 0] means Channel 1 trace.
        
        # Logic:
        # phase_diffs = np.arctan2(data_signal[idx, :], ref_signal[idx])*180/np.pi
        
        val_ref = data_signal[idx, 0] # Scalar
        vals_all = data_signal[idx, :] # Array (Channels)
        
        # arctan2(y, x)
        phase_diffs = np.arctan2(vals_all, val_ref) * 180 / np.pi
        
        # Plot
        num_channels = phase_diffs.shape[0]
        channels = np.arange(1, num_channels + 1)
        
        self.cycle_plot.clear()
        self.cycle_plot.plot(channels, phase_diffs, symbol='o', pen='b', brush='b', name="Poloidal Mode")
        self.cycle_plot.setTitle(f"Phase Differences at Time {self.sliced_time[idx]:.3f} ms", color="w", size="12pt")
        self.peaks_plot.setTitle(f"Wavelet Peaks at Time {self.sliced_time[idx]:.3f} ms", color="w", size="12pt")

    def on_plot_clicked(self, event):
        # Guide Manager Only
        self.guide_manager.handle_click(event)
