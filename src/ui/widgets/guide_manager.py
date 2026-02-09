# src/ui/widgets/guide_manager.py
import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Signal, Qt, QObject

class GuideManager(QObject):
    # Signal emitted when a new guide line is fixed
    # t1, c1, t2, c2, slope, velocity
    guide_updated = Signal(float, float, float, float, float, float)
    guide_cleared = Signal()
    
    def __init__(self, plot_widget):
        super().__init__()
        self.plot_widget = plot_widget
        self.guide_mode = False
        self.guide_start_point = None
        self.current_guide = None
        
        # Init Visuals
        self.guide_line = pg.PlotCurveItem(pen=pg.mkPen('r', width=1, style=Qt.DashLine))
        self.plot_widget.addItem(self.guide_line)
        
        # self.guide_marker = pg.ScatterPlotItem(size=10, pen=pg.mkPen('r'), brush=pg.mkBrush('r'))
        # self.plot_widget.addItem(self.guide_marker)
        
        # Connect Signals
        self.plot_widget.scene().sigMouseMoved.connect(self.on_mouse_move)
        
        # Setup UI
        self.setup_ui()
        
    def setup_ui(self):
        self.control_layout = QHBoxLayout()
        self.control_layout.setContentsMargins(0, 5, 0, 0)
        
        self.control_layout.addSpacing(5)
        self.btn_draw = QPushButton("Start Drawing")
        self.btn_draw.setFixedWidth(120)
        self.btn_draw.setCheckable(True)
        self.btn_draw.setStyleSheet("""
            QPushButton {
                background-color: #444; 
                color: white;
                border: none;
                padding: 6px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #222; /* Darker Orange for hover effect */
            }
            QPushButton:pressed {
                background-color: #111; /* Even darker for click effect */
            }
        """)
        self.btn_draw.toggled.connect(self.on_toggle_draw)
        self.control_layout.addWidget(self.btn_draw)
        
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setFixedWidth(100)
        self.btn_clear.setStyleSheet("""
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
        self.btn_clear.clicked.connect(self.clear_guide_click)
        self.control_layout.addWidget(self.btn_clear)
        
        self.lbl_info = QLabel("Fixed: N/A")
        self.lbl_info.setStyleSheet("color: #ffa500; font-weight: bold; margin-left: 10px;")
        self.control_layout.addWidget(self.lbl_info)
        
    def get_layout(self):
        return self.control_layout
        
    def on_toggle_draw(self, checked):
        self.guide_mode = checked
        if checked:
            self.btn_draw.setText("Stop Drawing")
            self.lbl_info.setText("Fixed: N/A")
            self.plot_widget.setCursor(Qt.CrossCursor)
        else:
            self.btn_draw.setText("Start Drawing")
            self.plot_widget.setCursor(Qt.ArrowCursor)
            self.guide_start_point = None # Cancel current operation if any
            
    def clear_guide_click(self):
        """User clicked clear button"""
        self.clear_guide()
        self.guide_cleared.emit()

    def clear_guide(self):
        self.guide_start_point = None
        self.guide_line.setData([], [])
        if hasattr(self, 'guide_marker'):
            self.guide_marker.setData([])
        # self.lbl_info.setText("Slope: N/A")
        self.current_guide = None
        self.lbl_info.setText("Fixed: N/A")
        
    def set_guide_line(self, t1, c1, t2, c2, slope, velocity):
        """Programmatically set the guide line (e.g. from sync)"""
        # Avoid re-emitting signals if unnecessary (handled by caller logic usually)
        
        self.guide_line.setData([t1, t2], [c1, c2])
        self.guide_line.setPen(pg.mkPen('r', width=2, style=Qt.SolidLine))
        if hasattr(self, 'guide_marker'):
            self.guide_marker.setData([t1], [c1]) # Show start point
        
        # Calculate visual angle for info if possible?
        # Skipping visual angle for sync as it depends on local viewbox/pixels
        
        self.lbl_info.setText(f"Fixed: ({t1:.1f}, {c1:.1f}) -> ({t2:.1f}, {c2:.1f})")
        self.current_guide = (t1, c1, t2, c2)
        
    def handle_click(self, event):
        """
        Returns True if the click was consumed by GuideManager.
        Call this from Parent's on_mouse_click.
        """
        if not self.guide_mode:
            return False
            
        pos = event.scenePos()
        mouse_point = self.plot_widget.plotItem.vb.mapSceneToView(pos)
        time = mouse_point.x()
        channel = mouse_point.y()
        
        if self.guide_start_point is None:
            # Step 1: Start
            self.guide_start_point = (time, channel)
            if hasattr(self, 'guide_marker'):
                self.guide_marker.setData([time], [channel])
            # self.lbl_info.setText("Click End Point")
        else:
            # Step 2: End
            self.guide_line.setPen(pg.mkPen('r', width=2, style=Qt.SolidLine))
            
            t1, c1 = self.guide_start_point
            t2, c2 = time, channel
            
            dt = t2 - t1
            dm = c2 - c1
            
            slope = 0
            velocity = 0
            if dt != 0:
                slope = dm / dt
                velocity = dt / dm if dm != 0 else 0
            
            self.lbl_info.setText(f"Fixed: ({t1:.1f}, {c1:.1f}) -> ({t2:.1f}, {c2:.1f})")
            self.current_guide = (t1, c1, t2, c2)
            
            # Emit Signal
            self.guide_updated.emit(t1, c1, t2, c2, slope, velocity)
            
            self.guide_start_point = None
            
        return True

    def on_mouse_move(self, pos):
        if not self.guide_mode or self.guide_start_point is None:
            return
            
        if self.plot_widget.plotItem.vb.sceneBoundingRect().contains(pos):
            mouse_point = self.plot_widget.plotItem.vb.mapSceneToView(pos)
            t_cur = mouse_point.x()
            m_cur = mouse_point.y()
            
            # Update Line
            self.guide_line.setData([self.guide_start_point[0], t_cur], [self.guide_start_point[1], m_cur])
            
            # Calc info
            t1, c1 = self.guide_start_point
            
            dt = t_cur - t1
            dm = m_cur - c1
            
            vis_info = ""
            if dt != 0:
                # Visual Angle
                p1_scene = self.plot_widget.plotItem.vb.mapViewToScene(pg.Point(t1, c1))
                p2_scene = pos
                dx_px = p2_scene.x() - p1_scene.x()
                dy_px = p2_scene.y() - p1_scene.y()
                visual_angle = np.degrees(np.arctan(abs(dx_px / dy_px))) if dy_px != 0 else 90.0
                vis_info = f" | Angle: {visual_angle:.0f}°"
            
            self.lbl_info.setText(f"Start: ({t1:.1f}, {c1:.1f}) | End: ({t_cur:.1f}, {m_cur:.1f}){vis_info}")
