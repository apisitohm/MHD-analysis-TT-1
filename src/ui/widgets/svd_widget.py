# src/ui/widgets/svd_widget.py
import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QPushButton, QSplitter)
from PySide6.QtCore import Qt
from src.data.analysis import SignalProcessor
from src.utils.config_manager import config_manager
_ui_conf = config_manager.get_config("ui", {})
_svd_conf = _ui_conf.get("svd_widget", {})
_analysis_conf = config_manager.get_config("analysis", {})

class SVDWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0,0,0,0)
        
        self.splitter = QSplitter(Qt.Vertical)
        self.layout.addWidget(self.splitter)
        
        # --- Top: Singular Values ---
        self.top_widget = QWidget()
        top_layout = QVBoxLayout(self.top_widget)
        top_layout.setContentsMargins(0,0,0,0)
        
        self.sv_plot = pg.PlotWidget()
        self.sv_plot.setTitle("Singular Values (Selected Mode: N/A)", color="w", size="12pt")
        self.sv_plot.setLabel('left', 'Singular Value')
        self.sv_plot.plotItem.getAxis('left').setPen(pg.mkPen('#ffffff', width=1))
        self.sv_plot.plotItem.getAxis('left').setTextPen(pg.mkPen('#ffffff', width=1))
        self.sv_plot.setLabel('bottom', 'Mode Index')
        self.sv_plot.plotItem.getAxis('bottom').setPen(pg.mkPen('#ffffff', width=1))
        self.sv_plot.plotItem.getAxis('bottom').setTextPen(pg.mkPen('#ffffff', width=1))
        self.sv_plot.showGrid(x=True, y=True, alpha=0.3)
        self.sv_plot.setXRange(-0.5, 14.5) # Fix X range for max 14 modes
        self.sv_plot.setMouseEnabled(x=False, y=True) # Lock X axis panning
        self.sv_plot.getPlotItem().setContentsMargins(10, 10, 20, 20)
        top_layout.addWidget(self.sv_plot)
        
        # Scatter for clickable points
        self.sv_line = self.sv_plot.plot(pen=pg.mkPen('y', width=2))
        self.sv_scatter = pg.ScatterPlotItem(size=12, pen=None, brush=pg.mkBrush('y'), hoverable=True)
        self.sv_scatter.sigClicked.connect(self.on_mode_clicked)
        self.sv_plot.addItem(self.sv_scatter)
        
        # Highlight for selected mode (Red Circle)
        self.selection_spot = pg.ScatterPlotItem(size=20, pen=pg.mkPen('r', width=1), brush=None)
        self.sv_plot.addItem(self.selection_spot)
        
        self.splitter.addWidget(self.top_widget)
        
        # --- Bottom: Spatial Structure ---
        self.bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(self.bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        
        self.spatial_plot = pg.PlotWidget()
        self.spatial_plot.plotItem.setTitle("Spatial Structure (Selected Mode: N/A)", color="w", size="12pt")
        self.spatial_plot.setLabel('left', 'High Field Side')
        self.spatial_plot.setLabel('bottom', 'Radial Position')
        self.spatial_plot.plotItem.getAxis('left').setPen(pg.mkPen('#ffffff', width=1))
        self.spatial_plot.plotItem.getAxis('left').setTextPen(pg.mkPen('#ffffff', width=1))
        self.spatial_plot.plotItem.getAxis('bottom').setPen(pg.mkPen('#ffffff', width=1))
        self.spatial_plot.plotItem.getAxis('bottom').setTextPen(pg.mkPen('#ffffff', width=1))
        self.spatial_plot.setAspectLocked(True)
        self.spatial_plot.showGrid(x=True, y=True, alpha=0.3)
        
        # Configurable range
        range_x = _svd_conf.get("plot_range_x", 60)
        range_y = _svd_conf.get("plot_range_y", 60)
        self.spatial_plot.setRange(xRange=(-range_x, range_x), yRange=(-range_y, range_y), padding=0)
        
        self.spatial_plot.setMouseEnabled(x=False, y=False) # Lock view if desired? User said "const limit", implies no auto-scaling.
        self.spatial_plot.getPlotItem().setContentsMargins(10, 10, 20, 20)
        bottom_layout.addWidget(self.spatial_plot)
        
        self.splitter.addWidget(self.bottom_widget)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)
        
        # State
        self.current_data = None
        self.current_time = None
        self.current_fs = 200000.0
        self.t_start = 0
        self.t_end = 0
        self.f_center = 0
        self.dfreq = 3000.0
        
        self.U = None
        self.S = None
        self.VT = None
        self.current_mode_idx = 0

    def set_context(self, data, time, fs, reset=True):
        self.current_data = data
        self.current_time = time
        self.current_fs = fs
        if reset:
            self.clear_plots()
        
    def clear_plots(self):
        self.sv_scatter.setData([])
        self.sv_line.setData([], [])
        self.spatial_plot.clear()
        self.U = None
        self.S = None

    def update_params(self, t_start, t_end, freq, dfreq):
        self.t_start = t_start
        self.t_end = t_end
        self.f_center = freq
        self.dfreq = dfreq
        
        self.calculate_svd()
        
    def refresh(self):
        """Refreshes the SVD calculation."""
        self.calculate_svd()

    def calculate_svd(self):
        if self.current_data is None:
            return
            
        sliced_time, filtered_T = SignalProcessor.compute_wavelet_data(
            self.current_data, self.current_time,
            self.t_start, self.t_end,
            self.f_center, self.dfreq,
            fs=self.current_fs
        )
        
        if filtered_T is None:
            return
            
        
        data_matrix = filtered_T.T
        
        U, S, VT = SignalProcessor.compute_svd(data_matrix)
        
        if U is None:
            return
            
        self.U = U
        self.S = S
        self.VT = VT
        
        # Plot Singular Values
        modes = np.arange(len(S))
        self.sv_scatter.setData(modes, S)
        self.sv_line.setData(modes, S)
        
        # Auto-scale X axis to number of modes
        self.sv_plot.setXRange(-0.5, len(S) - 0.5, padding=0)
        
        # Determine and set fixed Y range for this time slice to prevent selection from resizing it
        if len(S) > 0:
            s_min, s_max = np.min(S), np.max(S)
            diff = s_max - s_min
            if diff == 0:
                diff = 1.0 if s_max == 0 else abs(s_max) * 0.1
            
            # Add ~10% padding
            pad = diff * 0.1
            self.sv_plot.setYRange(s_min - pad, s_max + pad, padding=0)
        
        # Select first mode by default
        self.select_mode(0)

    def on_mode_clicked(self, plot, points):
        if len(points) > 0:
            pt = points[0]
            idx = int(pt.pos().x())
            self.select_mode(idx)
            
    def set_mode(self, mode):
        self.current_mode = mode
        if mode == 'm':
            self.spatial_plot.setLabel('left', 'High Field Side')
            self.spatial_plot.setLabel('bottom', 'Radial Position')
        else:
            self.spatial_plot.setLabel('left', 'Port O')
            self.spatial_plot.setLabel('bottom', 'Port K')

    def select_mode(self, idx):
        if self.U is None or idx >= self.U.shape[1]:
            return
            
        self.current_mode_idx = idx
        
        # Highlight selected point
        if self.S is not None and idx < len(self.S):
            self.selection_spot.setData([idx], [self.S[idx]])
        
        # Update title
        self.sv_plot.setTitle(f"Singular Values (Selected Mode: {idx})")
        self.spatial_plot.setTitle(f"Spatial Structure (Selected Mode: {idx})")

        # Get Spatial Mode (Column idx of U)
        spatial_vec = self.U[:, idx]
        
        # Determine num coils
        num_coils = len(spatial_vec)
        
        # Compute Structure
        
        res = SignalProcessor.compute_spatial_structure(spatial_vec, num_coils=num_coils)
        radius = _analysis_conf.get("spatial", {}).get("radius", 40)
        if res is None:
            return
            
        self.spatial_plot.clear()
        
        theta_points = _svd_conf.get("circle_points", 100)
        theta = np.linspace(0, 2*np.pi, theta_points)
        xc = radius * np.cos(theta)
        yc = radius * np.sin(theta)
        self.spatial_plot.plot(xc, yc, pen=pg.mkPen((100,100,100), width=1, style=Qt.DashLine))
        
        # Original Probes
        self.spatial_plot.plot(res['x_orig'], res['y_orig'], pen=None, symbol='o', symbolPen='w', symbolBrush='k', name='Original')
        
        # Displaced Probes
        self.spatial_plot.plot(res['x_disp'], res['y_disp'], pen=None, symbol='o', symbolPen=None, symbolBrush='r', name='Displaced')
        
        # Interpolated Curve
        self.spatial_plot.plot(res['x_smooth'], res['y_smooth'], pen=pg.mkPen('b', width=2), name='Interpolated')
        
        # Channel Labels
        for i in range(len(res['x_orig'])):
            x, y = res['x_orig'][i], res['y_orig'][i]
            # Place label slightly outside the circle (radius ~40 -> ~46)
            label = pg.TextItem(text=str(i+1), color='w', anchor=(0.5, 0.5))
            label.setPos(x * 1.15, y * 1.15)
            self.spatial_plot.addItem(label)
