# src/ui/widgets/wavelet_widget.py
import numpy as np
import pyqtgraph as pg
from scipy.ndimage import zoom
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Signal, Qt
# from src.data.analysis import SignalProcessor
from src.ui.widgets.guide_manager import GuideManager

from src.utils.config_manager import config_manager
_ui_conf = config_manager.get_config("ui", {})
_wave_ui_conf = _ui_conf.get("wavelet_widget", {})

class WaveletWidget(QWidget):
    time_point_selected = Signal(float, int) # time, channel_index
    # Signal to emit slope and velocity
    # (t1, c1, t2, c2, slope, velocity)
    guide_line_added = Signal(float, float, float, float, float, float) # slope (m/ms), velocity (ms/m)

    def __init__(self):
        super().__init__()
        self.zoom_range = None
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.plot_widget = pg.PlotWidget()
        # Scatter Plot for selected points
        # self.scatter = pg.ScatterPlotItem(size=10, pen=pg.mkPen(None), brush=pg.mkBrush(255, 0, 0, 255))
        # self.scatter.setZValue(100) # Ensure on top
        # self.plot_widget.addItem(self.scatter)
        self.selected_points = []
        self.plot_widget.setLabel('left', 'Channel')
        self.plot_widget.setLabel('bottom', 'Time', units='ms')
        # Set Mouse Mode to RectMode (Left Drag = Zoom Box)
        self.plot_widget.getViewBox().setMouseMode(pg.ViewBox.RectMode)
        self.plot_widget.getPlotItem().setContentsMargins(26, 10, 58, 10)
        self.plot_widget.setRange(xRange=(0, 500), yRange=(0.5, 12.5), padding=0)
        self.plot_widget.plotItem.getAxis('left').setPen(pg.mkPen('#ffffff', width=1))
        self.plot_widget.plotItem.getAxis('left').setTextPen(pg.mkPen('#ffffff', width=1))
        # self.plot_widget.plotItem.getAxis('right').setPen(pg.mkPen('#00ff00', width=1))
        self.plot_widget.plotItem.getAxis('bottom').setPen(pg.mkPen('#ffffff', width=1))
        self.plot_widget.plotItem.getAxis('bottom').setTextPen(pg.mkPen('#ffffff', width=1))
        self.layout.addWidget(self.plot_widget)

        self.img_item = pg.ImageItem()
        self.plot_widget.addItem(self.img_item)
        
        # Colormap
        # Using built-in colormap
        cmap = pg.colormap.get('viridis')
        self.img_item.setLookupTable(cmap.getLookupTable())
        
        # Click handling - Moved to GuideManager and on_mouse_click
        self.plot_widget.scene().sigMouseClicked.connect(self.on_mouse_click)
        
        # Range Change handling
        self.plot_widget.sigRangeChanged.connect(self.on_view_range_changed)
        
        # Guide Manager
        self.guide_manager = GuideManager(self.plot_widget)
        self.guide_manager.guide_updated.connect(self.guide_line_added.emit) # Re-emit for now
        
        # Setup Controls
        self.setup_controls()

    def setup_controls(self):
        # Insert GuideManager's layout
        # Note: GuideManager provides a QHBoxLayout
        self.layout.insertLayout(0, self.guide_manager.get_layout())
            
    # Removed old toggle/clear handlers as GuideManager handles them

    def update_plot(self, time_array, data_matrix, keep_view=False):
        """
        data_matrix: Shape (Time, Channel) (as output from analysis.py)
        time_array: Shape (Time,)
        """
        if time_array is None or data_matrix is None:
            self.img_item.clear()
            return
            
        # Display data
        # ImageItem expects [x, y] -> [Time, Channel]
        
        # Smoothing / Interpolation
        # Up-sample along the channel axis (axis 1) to create a smooth gradient
        # Zoom factor: 1 (no change in time), 10 (10x resolution in channels)
        try:
            smoothed_matrix = zoom(data_matrix, (1, _wave_ui_conf.get("zoom_factor", 10)), order=_wave_ui_conf.get("zoom_order", 1)) 
        except Exception as e:
            print(f"Smoothing Error: {e}")
            smoothed_matrix = data_matrix

        self.img_item.setImage(smoothed_matrix)
        
        # Scale
        # Channels are 1..N
        num_channels = data_matrix.shape[1]
        
        rect = [
            time_array[0],      # x min
            0.5,                # y min (Channel 1 centered at 1)
            time_array[-1] - time_array[0], # width
            num_channels        # height
        ]
        self.y_range = (0.5, num_channels + 0.5)
        self.x_range = (time_array[0], time_array[-1])
        self.img_item.setRect(rect)

        # Force ViewBox to match current data range (excludes old guide lines)
        # if keep_view and getattr(self, 'current_x_gap', None) is not None and getattr(self, 'current_y_gap', None) is not None:
        #      # Robust Offset Tracking
        #      current_x_offset = getattr(self, 'current_x_offset', 0)
        #      new_data_start = time_array[0]
             
        #      new_xmin = new_data_start + current_x_offset
        #      new_xmax = new_xmin + self.current_x_gap
             
        #      # print(f"  -> Applying Range: {new_xmin:.2f} to {new_xmax:.2f}")

        #      current_y_offset = getattr(self, 'current_y_offset', 0)
        #      new_data_ystart = 0.5
             
        #      new_ymin = new_data_ystart + current_y_offset
        #      new_ymax = new_ymin + self.current_y_gap
             
        #      self.plot_widget.setXRange(new_xmin, new_xmax, padding=0)
        #      self.plot_widget.setYRange(new_ymin, new_ymax, padding=0)
             
        # elif not keep_view:
        #     # print("  -> Resetting to Full Range")
        #     self.plot_widget.setXRange(*self.x_range, padding=0)
        #     self.plot_widget.setYRange(*self.y_range, padding=0)
        # self.plot_widget.autoRange()
        self.plot_widget.setXRange(*self.x_range, padding=0)
        self.plot_widget.setYRange(*self.y_range, padding=0)

    # on_mouse_move is now handled by GuideManager's internal connection.
    def set_default_view_range(self):
        self.plot_widget.setXRange(*self.x_range, padding=0)
        self.plot_widget.setYRange(*self.y_range, padding=0)

    def on_mouse_click(self, event):
        # Middle Click - Auto Range/Reset
        if event.button() == Qt.MiddleButton:
            self.set_default_view_range()
            return

        # Delegate to GuideManager first
        if self.guide_manager.handle_click(event):
            return

        try:
            pos = event.scenePos()
            mouse_point = self.plot_widget.plotItem.vb.mapSceneToView(pos)
            time = mouse_point.x()
            channel = mouse_point.y()
            
            # Standard Selection Logic
            channel_int = int(round(channel))
            
            # Emit
            self.time_point_selected.emit(time, channel_int)
            
            # Add to visual list
            self.selected_points.append({'pos': (time, channel_int), 'data': 1})
            if len(self.selected_points) > 2:
                self.selected_points.pop(0)
            # self.scatter.setData(self.selected_points)
        except Exception as e:
            print(f"Error in mouse click: {e}")
        

    def on_view_range_changed(self, _, ranges):
        # ranges is [[xmin, xmax], [ymin, ymax]]
        xmin, xmax = ranges[0]
        ymin, ymax = ranges[1]
        self.zoom_range = ranges
        # print(f"[WaveletWidget] View Range Changed: X=({xmin:.2f}, {xmax:.2f}), Y=({ymin:.2f}, {ymax:.2f})")
        
