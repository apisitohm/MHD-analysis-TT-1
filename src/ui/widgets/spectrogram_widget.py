# src/ui/widgets/spectrogram_widget.py
import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QLineEdit, QPushButton, QFrame, QApplication, QCheckBox, QComboBox)
from PySide6.QtCore import Qt, Signal
from src.data.analysis import SignalProcessor
from PySide6.QtGui import QDoubleValidator


class SpectrogramWidget(QWidget):
    # Signals to notify changes
    region_changed = Signal(float, float, float, float) # t_start, t_end, freq_center, dfreq
    request_overlay_load = Signal(str) # param_name

    def __init__(self):
        super().__init__()
        self.validator = QDoubleValidator(0.0, 999.0, 3)
        self.validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        
        self.layout = QVBoxLayout(self)
        # self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setContentsMargins(0,0,0,0)

        # Control Panel
        self.setup_controls()

        # Plot Widget
        self.plot_widget = pg.PlotWidget()
        # self.plot_widget.setZValue(60)
        self.plot_widget.setLabel('left', 'Frequency', units='Hz')
        self.plot_widget.setLabel('bottom', 'Time', units='ms')
        self.plot_widget.setRange(xRange=(0, 10), yRange=(1, 100),)
        self.plot_widget.getPlotItem().setContentsMargins(20, 10, 10, 10)
        self.layout.addWidget(self.plot_widget)
        
        # Image Item for Spectrogram
        self.img_item = pg.ImageItem()
        # self.img_item.setZValue(0) # Default is fine, Overlay is 100
        self.plot_widget.addItem(self.img_item)
        
        # Colormap
        self.hist = pg.HistogramLUTItem()
        self.hist.setImageItem(self.img_item)
        
        # IP Overlay (Secondary Axis)
        self.overlay_view = pg.ViewBox()
        self.overlay_view.setMouseMode(pg.ViewBox.RectMode) # Enable Box Zoom for Overlay too
        self.overlay_view.setZValue(50) # On top
        # MouseEnabled is managed by set_active_view
        self.plot_widget.plotItem.scene().addItem(self.overlay_view)
        self.plot_widget.plotItem.getAxis('right').linkToView(self.overlay_view)
        self.overlay_view.setXLink(self.plot_widget.plotItem)
        self.plot_widget.plotItem.getAxis('right').setLabel('Overlay', units='', color='#00ff00')
        self.plot_widget.plotItem.getAxis('right').setTextPen(pg.mkPen('#00ff00'))
        self.overlay_view.setYRange(0, 1)
        self.plot_widget.plotItem.getAxis('right').setWidth(50) # Fixed width for margin stability
        self.plot_widget.plotItem.showAxis('right') # Always visible as requested
        
        self.overlay_curve = pg.PlotCurveItem(pen=pg.mkPen('g', width=2))
        self.overlay_view.addItem(self.overlay_curve)
        
        # Link views
        self.plot_widget.plotItem.vb.sigResized.connect(self.update_views)
        
        # Interactions
        # Set Mouse Mode to RectMode (Left Drag = Zoom Box)
        self.plot_widget.getViewBox().setMouseMode(pg.ViewBox.RectMode)
        
        # Click handling (Middle Click Reset)
        self.plot_widget.scene().sigMouseClicked.connect(self.on_mouse_click)
        
        # Range Change handling
        self.plot_widget.sigRangeChanged.connect(self.on_view_range_changed)
        
        # Region of Interest (LinearRegionItem) for Time Selection
        self.time_roi = pg.LinearRegionItem(orientation=pg.LinearRegionItem.Vertical)
        self.time_roi.setZValue(10000) # Higher than overlay_view (50) to ensure grab priority
        for line in self.time_roi.lines:
            line.setPen(pg.mkPen((255, 255, 0, 128), width=1))
            line.setHoverPen(pg.mkPen((255, 255, 0, 128), width=4))
        self.plot_widget.addItem(self.time_roi)
        self.time_roi.sigRegionChanged.connect(self.on_roi_changed)
        
        # Line for Frequency Selection (InfiniteLine)
        self.freq_line = pg.InfiniteLine(angle=0, movable=True, 
                                        pen=pg.mkPen((255, 0, 0, 128), width=1), 
                                        hoverPen=pg.mkPen((255, 0, 0, 128), width=4))
        self.freq_line.setZValue(1000)
        self.plot_widget.addItem(self.freq_line)
        self.freq_line.sigPositionChanged.connect(self.on_freq_line_changed)
        
        # Setup Axis Clicks for Interaction Switching
        self.setup_axis_clicks()
        # Default to Main View Active
        self.set_active_view('main')

        self.current_data = None
        self.overlay_data = None
        self.overlay_time = None
        self.fs = 200000.0
        self.t_offset = 0.0

    def setup_axis_clicks(self):
        # Monkey patch mouse click events for axes to switch active view
        left_axis = self.plot_widget.plotItem.getAxis('left')
        right_axis = self.plot_widget.plotItem.getAxis('right')
        
        # Store original methods just in case (though we likely just overwrite or wrap)
        self._orig_left_click = left_axis.mouseClickEvent
        self._orig_right_click = right_axis.mouseClickEvent
        
        def on_left_click(event):
            if event.button() == Qt.LeftButton:
                self.set_active_view('main')
            if self._orig_left_click: self._orig_left_click(event)
            
        def on_right_click(event):
            if event.button() == Qt.LeftButton:
                self.set_active_view('overlay')
            if self._orig_right_click: self._orig_right_click(event)

        left_axis.mouseClickEvent = on_left_click
        right_axis.mouseClickEvent = on_right_click
        
    def set_active_view(self, view_name):
        print(f"[SpectrogramWidget] Switching to {view_name.upper()} view")
        if view_name == 'main':
            # Main Active, Overlay Passive (Transparent)
            self.overlay_view.setMouseEnabled(x=False, y=False)
            self.plot_widget.plotItem.vb.setMouseEnabled(x=True, y=True)
            self.plot_widget.plotItem.getAxis('left').setPen(pg.mkPen('#ffffff', width=2))
            self.plot_widget.plotItem.getAxis('left').setTextPen(pg.mkPen('#ffffff', width=2))
            self.plot_widget.plotItem.getAxis('right').setPen(pg.mkPen('#00ff00', width=1))
            self.plot_widget.plotItem.getAxis('bottom').setPen(pg.mkPen('#ffffff', width=1))
            self.plot_widget.plotItem.getAxis('bottom').setTextPen(pg.mkPen('#ffffff', width=1))
            
        elif view_name == 'overlay':
            # Overlay Active, Main Passive
            self.overlay_view.setMouseEnabled(x=True, y=True)
            self.plot_widget.plotItem.vb.setMouseEnabled(x=False, y=False)
            self.plot_widget.plotItem.getAxis('left').setPen(pg.mkPen('#ffffff', width=1))
            # self.plot_widget.plotItem.getAxis('left').setTextPen(pg.mkPen('#ffffff', width=1))
            self.plot_widget.plotItem.getAxis('right').setPen(pg.mkPen('#00ff00', width=2)) # Highlight
            self.plot_widget.plotItem.getAxis('right').setTextPen(pg.mkPen('#00ff00')) # Highlight
            self.plot_widget.plotItem.getAxis('bottom').setPen(pg.mkPen('#ffffff', width=1))
            self.plot_widget.plotItem.getAxis('bottom').setTextPen(pg.mkPen('#ffffff', width=1))

    def setup_controls(self):
        control_layout = QHBoxLayout()
        control_layout.setContentsMargins(0, 10, 0, 2)
        
        # Style for inputs
        input_style = "background-color: #2d2d2d; color: #ffffff; border: 1px solid #3e3e3e; padding: 2px;"

        # Config Group
        control_layout.addSpacing(10)
        control_layout.addWidget(QLabel("Window:"))
        self.txt_window = QLineEdit("200")
        self.txt_window.setFixedWidth(40)
        self.txt_window.setStyleSheet(input_style)
        control_layout.addWidget(self.txt_window)

        control_layout.addWidget(QLabel("NFFT:"))
        self.txt_nfft = QLineEdit("512")
        self.txt_nfft.setFixedWidth(40)
        self.txt_nfft.setStyleSheet(input_style)
        control_layout.addWidget(self.txt_nfft)

        # Separator
        line1 = QFrame()
        line1.setFrameShape(QFrame.VLine)
        line1.setFrameShadow(QFrame.Sunken)
        control_layout.addWidget(line1)

        # Time Group
        control_layout.addWidget(QLabel("Range(ms):"))
        self.txt_t_start = QLineEdit("0.000")
        self.txt_t_start.setFixedWidth(60)
        self.txt_t_start.setStyleSheet(input_style)
        control_layout.addWidget(self.txt_t_start)
        
        control_layout.addWidget(QLabel("-"))
        self.txt_t_end = QLineEdit("10.000")
        self.txt_t_end.setFixedWidth(60)
        self.txt_t_end.setStyleSheet(input_style)
        control_layout.addWidget(self.txt_t_end)

        # Separator
        line2 = QFrame()
        line2.setFrameShape(QFrame.VLine)
        line2.setFrameShadow(QFrame.Sunken)
        control_layout.addWidget(line2)

        # Freq Group
        control_layout.addWidget(QLabel("Freq center(kHz):"))
        self.txt_f_center = QLineEdit("10.000") # Default 10kHz
        self.txt_f_center.setToolTip("Frequency center in kHz")
        self.txt_f_center.setFixedWidth(80)
        self.txt_f_center.setStyleSheet(input_style)
        control_layout.addWidget(self.txt_f_center)
        
        control_layout.addWidget(QLabel("Freq width(kHz):"))
        self.txt_f_width = QLineEdit("3.000") # Default 3kHz
        self.txt_f_width.setToolTip("Frequency width in kHz")
        self.txt_f_width.setFixedWidth(60)
        self.txt_f_width.setStyleSheet(input_style)
        self.txt_f_width.setValidator(self.validator)
        control_layout.addWidget(self.txt_f_width)
        
        self.btn_set = QPushButton("Set")
        self.btn_set.setFixedWidth(50)
        self.btn_set.setStyleSheet("""
            QPushButton {
                background-color: #007acc; 
                color: white;
                border: none;
                padding: 6px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0062a3; /* Darker Orange for hover effect */
            }
            QPushButton:pressed {
                background-color: #004a7a; /* Even darker for click effect */
            }
        """)
        self.btn_set.clicked.connect(self.on_set_clicked)
        control_layout.addWidget(self.btn_set)
        
        # Separator
        line3 = QFrame()
        line3.setFrameShape(QFrame.VLine)
        line3.setFrameShadow(QFrame.Sunken)
        control_layout.addWidget(line3)
        
        # Overlay Controls
        # control_layout.addSpacing(10)
        control_layout.addWidget(QLabel("Parameter:"))
        self.combo_overlay_param = QComboBox()
        self.combo_overlay_param.setEditable(True)
        self.combo_overlay_param.setInsertPolicy(QComboBox.NoInsert)
        self.combo_overlay_param.setFixedWidth(100)
        self.combo_overlay_param.setStyleSheet(input_style)
        # Add a default or wait for main window to populate
        self.combo_overlay_param.addItem("IP1") 
        control_layout.addWidget(self.combo_overlay_param)
        
        self.btn_overlay_plot = QPushButton("Plot")
        self.btn_overlay_plot.setFixedWidth(70)
        self.btn_overlay_plot.setStyleSheet("""
            QPushButton {
                background-color: #2d5a2d; 
                color: white;
                border: none;
                padding: 6px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #224422; /* Darker Orange for hover effect */
            }
            QPushButton:pressed {
                background-color: #112211; /* Even darker for click effect */
            }
        """)
        self.btn_overlay_plot.clicked.connect(self.on_overlay_plot_clicked)
        control_layout.addWidget(self.btn_overlay_plot)
        
        self.btn_overlay_clear = QPushButton("Clear")
        self.btn_overlay_clear.setFixedWidth(70)
        self.btn_overlay_clear.setStyleSheet("""
            QPushButton {
                background-color: #a83232; 
                color: white;
                border: none;
                padding: 6px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #8a2424; /* Darker Orange for hover effect */
            }
            QPushButton:pressed {
                background-color: #6c1a1a; /* Even darker for click effect */
            }
        """)
        self.btn_overlay_clear.clicked.connect(self.on_overlay_clear_clicked)
        control_layout.addWidget(self.btn_overlay_clear)

        control_layout.addStretch()
        self.layout.addLayout(control_layout)

    def update_views(self):
        self.overlay_view.setGeometry(self.plot_widget.plotItem.vb.sceneBoundingRect())
        self.overlay_view.linkedViewChanged(self.plot_widget.plotItem.vb, self.overlay_view.XAxis)

    def set_param_options(self, options):
        current = self.combo_overlay_param.currentText()
        self.combo_overlay_param.clear()
        self.combo_overlay_param.addItems(options)
        # Restore if possible, or set default
        index = self.combo_overlay_param.findText(current)
        if index >= 0:
            self.combo_overlay_param.setCurrentIndex(index)

    def set_overlay_data(self, time, data, label=None, units=None):
        self.overlay_time = time
        self.overlay_data = data
        if label:
            self.plot_widget.plotItem.getAxis('right').setLabel(label, units=units, color='#00ff00')
        self.update_overlay_plot()
        
    def update_overlay_plot(self):
        if self.overlay_data is not None and self.overlay_time is not None:
            self.overlay_curve.setData(self.overlay_time, self.overlay_data)
            # self.overlay_curve.setZValue(100) # Handled by ViewBox Z
            self.overlay_view.enableAutoRange(axis=pg.ViewBox.YAxis)
        else:
            self.overlay_curve.clear()
            self.overlay_curve.update() 
            self.overlay_view.update() # Force view update
            self.plot_widget.plotItem.update() # Force main plot update
            self.overlay_view.setYRange(0, 1)
            self.plot_widget.plotItem.getAxis('right').setLabel("Overlay", units="", color='#00ff00')
            # self.plot_widget.plotItem.hideAxis('right') # Keep visible as requested
            
    def on_overlay_plot_clicked(self):
        param = self.combo_overlay_param.currentText()
        if param:
            self.request_overlay_load.emit(param)
            
    def on_overlay_clear_clicked(self):
        self.overlay_data = None
        self.overlay_time = None
        
        self.update_overlay_plot()

    def set_data(self, data, fs, t_offset=0, keep_view=False):
        self.current_data = data
        self.fs = fs
        self.t_offset = t_offset
        
        self.fs = fs
        self.t_offset = t_offset
        
        # Save current view state if requested
        saved_state = {}
        if keep_view:
            pass # Keep IP data
        else:
            self.overlay_data = None
            self.overlay_time = None
            self.update_overlay_plot()

        if keep_view:
            saved_state['view_range'] = self.plot_widget.viewRange()
            saved_state['freq_val'] = self.freq_line.value()
            saved_state['roi_region'] = self.time_roi.getRegion()
            # Also text values? kept in textboxes

        self.compute_and_plot()
        
        # Reset default view range (will be set by parent if needed)
        self.default_view_range = None
        
        if keep_view:
            # Restore view state
            self.plot_widget.setRange(xRange=saved_state['view_range'][0], yRange=saved_state['view_range'][1], padding=0)
            self.freq_line.setValue(saved_state['freq_val'])
            self.time_roi.setRegion(saved_state['roi_region'])
        else:
            self.plot_widget.autoRange()
            # Initial defaults
            t_min = self.times_ms[0]
            t_max = self.times_ms[-1]
            t_mid = (t_min + t_max) / 2
            range_t = (t_max - t_min) * 0.1
            if range_t == 0: range_t = 1.0
            
            self.time_roi.setRegion([t_mid - range_t, t_mid + range_t])
            
            # f_mid = (self.freqs[0] + self.freqs[-1]) / 2
            # self.freq_line.setValue(f_mid)
            self.freq_line.setValue(10000.0) # Default to 10kHz as requested

        # Initial Sync
        self.update_ui_from_plot()
        self.update_ui_from_freq_line()
        
        # Emit initial
        self.emit_region_changed()

    def compute_and_plot(self):
        if self.current_data is None:
            return

        # Get params from UI or defaults
        try:
            nfft = int(self.txt_nfft.text())
        except:
            nfft = 512
            self.txt_nfft.setText("512")
            
        try:
            win_size = int(self.txt_window.text())
        except:
            win_size = 200 # Approx 1ms at 200k? 200k/1000 = 200.
            self.txt_window.setText("200")



        # Compute Spectrogram
        # nperseg = win_size
        freq, times, Sxx = SignalProcessor.compute_spectrogram(
            self.current_data, self.fs,nperseg=win_size ,nfft=nfft
        )
        
        self.freqs = freq
        if len(freq) > 0:
            pass
            # print(f"DEBUG: compute_and_plot: freq min={freq[0]}, max={freq[-1]}, len={len(freq)}")
        
        Sxx_log = 10 * np.log10(Sxx + 1e-9) 
        
        self.img_item.setImage(Sxx_log.T)
        
        # Scale axes
        times_ms = (times * 1000) + (self.t_offset * 1000)
        self.times_ms = times_ms
        
        rect = [times_ms[0], freq[0], times_ms[-1]-times_ms[0], freq[-1]-freq[0]]
        self.img_item.setRect(rect)

    def on_roi_changed(self):
        # Update text boxes from ROI
        region = self.time_roi.getRegion()
        self.txt_t_start.setText(f"{region[0]:.3f}")
        self.txt_t_end.setText(f"{region[1]:.3f}")
        
        self.emit_region_changed()

    def on_freq_line_changed(self):
        self.update_ui_from_freq_line()
        self.emit_region_changed()

    def update_ui_from_plot(self):
        t_start, t_end = self.time_roi.getRegion()
        self.txt_t_start.setText(f"{t_start:.3f}")
        self.txt_t_end.setText(f"{t_end:.3f}")

    def update_ui_from_freq_line(self):
        val = self.freq_line.value()
        # Convert Hz to kHz for display
        self.txt_f_center.setText(f"{val/1000.0:.3f}")

    def on_set_clicked(self):
        # Update Plot from UI
        self.btn_set.setEnabled(False)
        self.btn_set.setText("...")
        QApplication.processEvents()
        
        try:
            t_start = float(self.txt_t_start.text())
            t_end = float(self.txt_t_end.text())
            self.time_roi.setRegion([t_start, t_end])
            
            # Read from UI
            val_f = float(self.txt_f_center.text())
            val_df = float(self.txt_f_width.text())
            self.txt_f_width.setText(f"{val_df:.3f}")
            
            # Convert kHz to Hz for internal logic
            f_hz = val_f * 1000.0
            df_hz = val_df * 1000.0
            
            self.freq_line.setValue(f_hz)
            
            # Recompute if params changed (NFFT/Win)
            self.compute_and_plot()
            self.emit_region_changed()
            
        except ValueError:
            print("Invalid input in Spectrogram settings") # Invalid input
        finally:
            self.btn_set.setEnabled(True)
            self.btn_set.setText("Set")

    def emit_region_changed(self):
        try:
            t_start = float(self.txt_t_start.text())
            t_end = float(self.txt_t_end.text())
            
            # Freq center from line (Hz)
            f_center = self.freq_line.value()
            
            # Freq width from text box (take existing value, convert to Hz)
            f_width_khz = float(self.txt_f_width.text())
            f_width = f_width_khz * 1000.0
            
            self.region_changed.emit(t_start, t_end, f_center, f_width)
            
        except ValueError:
            pass

    def set_default_view_range(self, t_min, t_max, update_plot=True):
        """Store the initial 'smart' view range (e.g. plasma duration) for reset."""
        self.default_view_range = (t_min, t_max)
        print(f"[SpectrogramWidget] Default View Range Set: X={self.default_view_range}")
        if update_plot:
            self.plot_widget.setXRange(t_min, t_max, padding=0)
            self.plot_widget.setYRange(0, self.freqs[-1] + 1000, padding=0)

    def on_mouse_click(self, event):
        # Middle Click - Auto Range/Reset
        if event.button() == Qt.MiddleButton:
            # Check if we have a smart default range (Plasma Duration)
            if hasattr(self, 'default_view_range') and self.default_view_range:
                 t_min, t_max = self.default_view_range
                 
                 if hasattr(self, 'freqs') and self.freqs is not None and len(self.freqs) > 0:
                     f_min = self.freqs[0]
                     f_max = self.freqs[-1] + 1000
                     self.plot_widget.setRange(xRange=(t_min, t_max), yRange=(f_min, f_max), padding=0)
                 else:
                     self.plot_widget.setXRange(t_min, t_max)
                     self.plot_widget.plotItem.autoRange() # Reset Y if needed
            
            # Fallback to full data range
            # elif hasattr(self, 'times_ms') and self.times_ms is not None and len(self.times_ms) > 0:
            #     t_min = self.times_ms[0]
            #     t_max = self.times_ms[-1]
                
            #     if hasattr(self, 'freqs') and self.freqs is not None and len(self.freqs) > 0:
            #          f_min = self.freqs[0]
            #          f_max = self.freqs[-1]
            #          self.plot_widget.setRange(xRange=(t_min, t_max), yRange=(f_min, f_max))
            #     else:
            #          self.plot_widget.setRange(xRange=(t_min, t_max))
            #          self.plot_widget.plotItem.autoRange()
            else:
                 self.plot_widget.plotItem.autoRange()
                 
            # 2. Reset Overlay if it exists
            if self.overlay_view:
                self.overlay_view.enableAutoRange(axis=pg.ViewBox.YAxis)
                
            print("[SpectrogramWidget] View Reset to Default/Full")
            return

    def on_view_range_changed(self, _, ranges):
        # ranges is [[xmin, xmax], [ymin, ymax]]
        xmin, xmax = ranges[0]
        ymin, ymax = ranges[1]
        print(f"[SpectrogramWidget] View Range Changed: X=({xmin:.2f}, {xmax:.2f}), Y=({ymin:.2f}, {ymax:.2f})")

