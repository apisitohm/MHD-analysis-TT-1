# src/ui/dialogs/init_phase_dialog.py
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QSlider, QDoubleSpinBox, QScrollArea, QWidget, 
                            QDialogButtonBox, QFrame)
from PySide6.QtCore import Qt, Signal

class InitPhaseDialog(QDialog):
    # Emits dict {channel_index: offset_ms}
    # channel_index is 0-based
    # Use 'object' to avoid Shiboken conversion issues with dicts
    t0_changed = Signal(object)
    
    def __init__(self, channel_names, type_str, t0_offsets, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Setup Init Phase (t0)")
        self.resize(400, 500)
        self.type_str = type_str
        self.channel_names = channel_names
        # Ensure deep copy of offsets to avoid direct mutation before signal
        self.current_offsets = t0_offsets.copy()
        
        # Main Layout
        layout = QVBoxLayout(self)
        
        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        
        # Header
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Channel"))
        header_layout.addWidget(QLabel(f"t0 (\u03bcs)"))
        header_layout.addWidget(QLabel("Value"))
        self.content_layout.addLayout(header_layout)
        
        # Dynamic Rows
        self.sliders = {}
        self.spinboxes = {}
        
        for i, name in enumerate(self.channel_names):
            row_layout = QHBoxLayout()
            
            # Label
            lbl = QLabel(f"{name}{self.type_str}")
            lbl.setFixedWidth(50)
            row_layout.addWidget(lbl)
            
            # Current value in ms
            val_ms = self.current_offsets.get(i, 0.0)
            val_us = int(val_ms * 1000.0)
            
            # Slider (-100 to +100 us)
            slider = QSlider(Qt.Horizontal)
            slider.setRange(-100, 100)
            slider.setValue(val_us)
            slider.valueChanged.connect(lambda val, idx=i: self.on_slider_changed(val, idx))
            row_layout.addWidget(slider)
            
            # SpinBox (-100 to +100 us)
            spin = QDoubleSpinBox()
            spin.setRange(-100, 100)
            spin.setSingleStep(1)
            spin.setDecimals(0)
            spin.setValue(val_us)
            spin.valueChanged.connect(lambda val, idx=i: self.on_spin_changed(val, idx))
            spin.setFixedWidth(100)
            row_layout.addWidget(spin)
            
            # Store references
            self.sliders[i] = slider
            self.spinboxes[i] = spin
            
            self.content_layout.addLayout(row_layout)
            
            # Separator
            line = QFrame()
            line.setFrameShape(QFrame.HLine)
            line.setFrameShadow(QFrame.Sunken)
            self.content_layout.addWidget(line)
            
        self.content_layout.addStretch()
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def on_slider_changed(self, val, idx):
        # val is int (us)
        # Update spinbox without triggering signal loop
        spin = self.spinboxes[idx]
        spin.blockSignals(True)
        spin.setValue(val)
        spin.blockSignals(False)
        
        self.update_offset(idx, val)
        
    def on_spin_changed(self, val, idx):
        # val is float (us) from DoubleSpinBox, but decimals=0 so essentially int
        val_int = int(val)
        
        # Update slider
        slider = self.sliders[idx]
        slider.blockSignals(True)
        slider.setValue(val_int)
        slider.blockSignals(False)
        
        self.update_offset(idx, val_int)
        
    def update_offset(self, idx, val_us):
        # Convert us -> ms for the backend
        val_ms = val_us / 1000.0
        self.current_offsets[idx] = val_ms
        self.t0_changed.emit(self.current_offsets)
