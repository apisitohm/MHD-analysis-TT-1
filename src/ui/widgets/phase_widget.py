# src/ui/widgets/phase_widget.py
import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QPushButton, QSplitter, QCheckBox)
from PySide6.QtCore import Signal, Qt
from src.ui.widgets.guide_manager import GuideManager
from src.data.analysis import SignalProcessor

class PhaseWidget(QWidget):
    # Signals
    fit_requested = Signal(float, float, float) 
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
        self.info_label = QLabel("Select 2 points to fit.")
        self.controls_layout.addWidget(self.info_label)
        
        self.lock_check = QCheckBox("Lock Result")
        self.controls_layout.addWidget(self.lock_check)
        
        # Peaks Plot (Initialize earlier to pass to GuideManager)
        self.peaks_plot = pg.PlotWidget()
        self.peaks_plot.setTitle("Wavelet Peaks", color="w", size="12pt")
        self.peaks_plot.setLabel('left', 'Channel')
        self.peaks_plot.setLabel('bottom', 'Time', units='ms')
        self.peaks_plot.plotItem.getAxis('left').setPen(pg.mkPen('#ffffff', width=1))
        self.peaks_plot.plotItem.getAxis('left').setTextPen(pg.mkPen('#ffffff', width=1))
        # self.peaks_plot.plotItem.getAxis('right').setPen(pg.mkPen('#00ff00', width=1))
        self.peaks_plot.plotItem.getAxis('bottom').setPen(pg.mkPen('#ffffff', width=1))
        self.peaks_plot.plotItem.getAxis('bottom').setTextPen(pg.mkPen('#ffffff', width=1))
        # Set Mouse Mode to RectMode (Left Drag = Zoom Box)
        self.peaks_plot.getViewBox().setMouseMode(pg.ViewBox.RectMode)
        
        # Guide Manager
        self.guide_manager = GuideManager(self.peaks_plot)

        
        # Guide Line Info - Remove old label if GuideManager covers it
        # self.lbl_guide_angle = QLabel("Guide: N/A")
        # self.controls_layout.addWidget(self.lbl_guide_angle)
        
        self.controls_layout.addStretch()
        self.top_layout.addLayout(self.controls_layout)
        self.top_layout.addWidget(self.peaks_plot)
        
        self.peaks_scatter = pg.ScatterPlotItem(size=10, pen=pg.mkPen(None), brush=pg.mkBrush(255, 255, 0, 200)) # Yellow peaks
        self.peaks_plot.addItem(self.peaks_scatter)
        self.peaks_plot.getPlotItem().setContentsMargins(10, 10, 20, 20) # Extra bottom/right for labels
        
        # ...
        
        # Selection Scatter (Highlights)
        self.selection_scatter = pg.ScatterPlotItem(size=15, pen=pg.mkPen('g', width=2), brush=pg.mkBrush(None))
        self.peaks_plot.addItem(self.selection_scatter)
        
        # Click Handling
        self.peaks_plot.scene().sigMouseClicked.connect(self.on_plot_clicked)
        self.peaks_plot.sigRangeChanged.connect(self.on_view_range_changed)
        
        self.splitter.addWidget(self.top_widget)
        
        # --- Bottom Row: Phase Fit ---
        self.bottom_widget = QWidget()
        self.bottom_layout = QVBoxLayout(self.bottom_widget)
        self.bottom_layout.setContentsMargins(0,0,0,0)
        
        self.fit_plot = pg.PlotWidget()
        self.fit_plot.setLabel('left', 'Phase Difference', units='deg')
        self.fit_plot.setLabel('bottom', 'Coil Location', units='deg')
        self.fit_plot.showGrid(x=True, y=True, alpha=0.3)
        self.fit_plot.getPlotItem().setContentsMargins(10, 10, 20, 20)
        self.fit_plot.getPlotItem().getAxis('left').setPen(pg.mkPen('#ffffff', width=1))
        self.fit_plot.getPlotItem().getAxis('left').setTextPen(pg.mkPen('#ffffff', width=1))
        self.fit_plot.getPlotItem().getAxis('bottom').setPen(pg.mkPen('#ffffff', width=1))
        self.fit_plot.getPlotItem().getAxis('bottom').setTextPen(pg.mkPen('#ffffff', width=1))

        self.bottom_layout.addWidget(self.fit_plot)
        
        self.splitter.addWidget(self.bottom_widget)
        
        # State
        self.current_data = None
        self.current_time = None
        self.current_t_start = 0
        self.current_t_end = 0
        self.current_freq = 0
        self.current_dfreq = 3000.0
        self.current_mode = 'm'
        self.fit_plot.setTitle(f"Slope [{self.current_mode} mode] = N/A, R<sup>2</sup> = N/A", color="w", size="12pt")
        
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
             
        # Update Fit Plot title placeholder
        self.fit_plot.setTitle(f"Slope [{self.current_mode} mode] = N/A, R<sup>2</sup> = N/A", color="w", size="12pt")

        
    def on_view_range_changed(self, _, ranges):
        if self._updating:
            return
            
        # ranges is [[xmin, xmax], [ymin, ymax]]
        xmin, xmax = ranges[0]
        # ymin, ymax = ranges[1]
        
        if hasattr(self, 'x_range') and self.x_range:
            spec_start = self.x_range[0]
            # spec_end = self.x_range[1]
            
            # Sync Logic: Track offsets relative to Spectrogram Start
            self.current_x_offset = xmin - spec_start
            self.current_x_gap = xmax - xmin
            
            # Emit Signal
            self.view_zoom_changed.emit(self.current_x_offset, self.current_x_gap)
            
            # Debug (Optional - keep enabled for now as requested)
            # print(f"Spec Start: {spec_start:.4f} | Zoom Start: {xmin:.4f} | Offset: {self.current_x_offset:.4f} | Width: {self.current_x_gap:.4f}")

    def set_zoom_state(self, offset, width):
        self.current_x_offset = offset
        self.current_x_gap = width
        
        # Apply immediately if possible
        if self.isVisible() and self.current_t_start != 0:
             self.zoom_to_range(self.current_t_start, offset, width)

    def set_context(self, data, time, fs=200000.0, reset=True):
        """Sets the raw data context."""
        self.current_data = data
        self.current_time = time
        self.current_fs = fs
        
        # Always clear data-dependent calculations
        self.peaks_data = []
        # self.selected_points = [] # Keep selection if dragging? No, t0 shift invalidates time points?
        
        if reset:
            self.selected_points = []
            self.peaks_scatter.setData([])
            self.selection_scatter.setData([])
            self.calc_btn.setChecked(False)
            self.calc_btn.setText("Enable Wavelet Peaks")
            self.fit_plot.clear()
            self.lock_check.setChecked(False)
            
            # Reset Zoom Tracking
            self.current_x_offset = 0
            self.current_x_gap = None
        else:
            # If not resetting, we preserve the selection
            pass

    def update_params(self, t_start, t_end, freq, dfreq=3000.0, keep_view=False):
        """Updates parameters from Spectrogram/Controls."""
        
        # Cache current zoom state to avoid corruption during update
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
            # Update internal state too
            self.current_x_offset = 0
            self.current_x_gap = None
        else:
            # If width is same (Pan), we want to KEEP the relative zoom
            pass
        
        if self.calc_btn.isChecked():
            self.calculate_peaks(keep_view=keep_view)
            
            if saved_gap is not None:
                # Explicitly zoom using stored gaps
                self.zoom_to_range(t_start, saved_offset, saved_gap)

    def zoom_to_range(self, spec_start, start_gap, zoom_width):
        self._updating = True
        try:
            # print(f"Zooming to range: {spec_start + start_gap} to {spec_start + start_gap + zoom_width}")
            self.peaks_plot.setXRange(spec_start + start_gap, spec_start + start_gap + zoom_width, padding=0)
        finally:
            self._updating = False

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
            self.selection_scatter.setData([]) # Clear selections too?
            self.selected_points = []
            
    def refresh(self, keep_view=False):
        """Refreshes the plot calculation."""
        if self.calc_btn.isChecked():
            self.calculate_peaks(keep_view=keep_view)

    def calculate_peaks(self, keep_view=False):
        if self.current_data is None:
            return
            
        sliced_time, filtered_data_T = SignalProcessor.compute_wavelet_data(
            self.current_data, self.current_time, 
            self.current_t_start, self.current_t_end, 
            self.current_freq, self.current_dfreq, 
            fs=self.current_fs
        )
        
        if sliced_time is None:
            return
            
        # filtered_data_T is (Time, Channels). Need (Channels, Time) for peak finding per ch
        filtered_data = filtered_data_T.T 
        
        # fs=200k -> 0.1ms = 20 samples.
        # min distance = 1/freq * fs * 0.5?
        
        dist = int((1.0 / (self.current_freq + 1e-9)) * self.current_fs * 0.5)
        dist = max(1, dist)
        
        peaks = SignalProcessor.find_all_peaks(sliced_time, filtered_data, distance=dist)
        self.peaks_data = peaks
        
        x = [p['t'] for p in peaks]
        y = [p['ch'] for p in peaks]
        self.peaks_scatter.setData(x, y)
        
        # Determine Data Range (ROI)
        # Sliced time tells us the data range
        self.x_range = (self.current_t_start, self.current_t_end)
        self.y_range = (0.5, 12.5 if self.current_mode == 'm' else 14.5)
        
        # Autozoom x to range OR Restore Offset
        if not keep_view:
            self.peaks_plot.setXRange(self.current_t_start, self.current_t_end)
            if self.current_mode == 'm':
                self.peaks_plot.setYRange(0.5, 12.5, padding=0.0) # 12 channels
            else:
                self.peaks_plot.setYRange(0.5, 14.5, padding=0.0) # 14 channels
        
        # We assume update_params will call zoom_to_range if keep_view is True
        if keep_view and len(self.selected_points) == 2:
            if not self.lock_check.isChecked():
                self.re_snap_selection()

    def re_snap_selection(self):
        new_selected = []
        for pt in self.selected_points:
            target_ch = pt['ch']
            # Find closest peak in new peaks_data
            candidates = [p for p in self.peaks_data if p['ch'] == target_ch]
            if candidates:
                # Find closest in absolute time (assume shifts are small or we track the feature)
                closest = min(candidates, key=lambda p: abs(p['t'] - pt['t']))
                # Only snap if within reasonable distance (e.g. < 5ms? or just snap to nearest?)
                # Since t0 shift might be large, snapping to nearest on same channel is best guess
                new_selected.append(closest)
            else:
                # If peak lost, maybe keep old point? or invalid?
                # For now, keep old point to avoid crash
                new_selected.append(pt)
        
        self.selected_points = new_selected
        
        # Update Visuals
        x = [p['t'] for p in self.selected_points]
        y = [p['ch'] for p in self.selected_points]
        self.selection_scatter.setData(x, y)
        
        if len(self.selected_points) == 2:
            self.perform_fit()

    def on_plot_clicked(self, event):
        # Delegate to GuideManager
        if self.guide_manager.handle_click(event):
            return
            
        # Middle Click - Auto Range
        if event.button() == Qt.MiddleButton:
            self.peaks_plot.plotItem.autoRange()
            return
            
        if not self.calc_btn.isChecked():
            return
            
        pos = event.scenePos()
        if self.peaks_plot.plotItem.vb.sceneBoundingRect().contains(pos):
            mouse_point = self.peaks_plot.plotItem.vb.mapSceneToView(pos)
            mx, my = mouse_point.x(), mouse_point.y()
            
            target_ch = int(round(my))
            
            # Filter peaks by channel
            candidates = [p for p in self.peaks_data if p['ch'] == target_ch]
            
            if not candidates:
                return
                
            # Find closest in time
            closest = min(candidates, key=lambda p: abs(p['t'] - mx))
            
            # Check within reasonable threshold?
            if abs(closest['t'] - mx) < 0.5: # 0.5 ms tolerance?
                self.select_point(closest)

    def select_point(self, point):
        # Add to selected
        if point in self.selected_points:
            return
            
        self.selected_points.append(point)
        if len(self.selected_points) > 2:
            self.selected_points.pop(0)
            
        # Update Visuals
        x = [p['t'] for p in self.selected_points]
        y = [p['ch'] for p in self.selected_points]
        self.selection_scatter.setData(x, y)
        
        self.info_label.setText(f"Selected: {len(self.selected_points)} points")
        
        if len(self.selected_points) == 2:
            self.perform_fit()

    def perform_fit(self):
        p1 = self.selected_points[0]
        p2 = self.selected_points[1]
        
        t1, c1 = p1['t'], p1['ch']
        t2, c2 = p2['t'], p2['ch']
        
        print(f"Fit Request: {t1:.4f}, {c1} -> {t2:.4f}, {c2}")
        
        # Determine coils and excludes based on mode
        excluded = []
        num_coils = 12
        if self.current_mode == 'n': # Toroidal
             num_coils = 14
        
        # Use simple distance for peak finding if not already refined
        # `self.peaks_data` already contains ALL peaks for the view range.
        
        # Call robust calc
        # Note: logic requires peaks for ALL channels. `self.peaks_data` has them.
        
        angles, dphase, result_times = SignalProcessor.calculate_phase_diffs_robust(
            self.peaks_data, p1, p2, self.current_freq, 
            num_coils=num_coils, excluded_channels=excluded
        )
        
        if angles is not None:
            self.update_fit_plot(angles, dphase)
            
    def update_fit_plot(self, channel_angles, phase_diffs):
        self.fit_plot.clear()
        self.fit_plot.plot(channel_angles, phase_diffs, pen=None, symbol='o', name='Data')
        
        if len(channel_angles) > 1:
            coeffs = np.polyfit(channel_angles, phase_diffs, 1)
            slope, intercept = coeffs
            
            x_fit = np.array([min(channel_angles), max(channel_angles)])
            y_fit = slope * x_fit + intercept
            
            self.fit_plot.plot(x_fit, y_fit, pen='r', name='Fit')
            
             # R2
            y_mean = np.mean(phase_diffs)
            ss_tot = np.sum((phase_diffs - y_mean)**2)
            ss_res = np.sum((phase_diffs - (slope * channel_angles + intercept))**2)
            r2 = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
            
            self.fit_plot.setTitle(f"Slope [{self.current_mode} mode] = {slope:.2f}, R<sup>2</sup> = {r2:.2f}", color="w", size="12pt")
            self.fit_plot.showGrid(x=True, y=True, alpha=0.3)
            # self.fit_plot.setLabel('left', 'Phase Difference', units='deg')
            # self.fit_plot.setLabel('bottom', 'Channel Angle', units='deg')
            

