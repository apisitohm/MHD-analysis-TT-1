# src/ui/dialogs/amplitude_multiplier_dialog.py
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QSlider, QDoubleSpinBox, QScrollArea, QWidget, 
                               QDialogButtonBox, QFrame)
from PySide6.QtCore import Qt, Signal

class AmplitudeMultiplierDialog(QDialog):
    # Emits dict {channel_index: multiplier_float}
    # channel_index is 0-based
    # multiplier_float: 1.0 = 100%, 0.0 = 0%, 2.0 = 200%
    amplitude_changed = Signal(object)
    
    def __init__(self, channel_names, type_str, current_multipliers, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Setup Amplitude Multiplier")
        self.resize(400, 500)
        self.type_str = type_str
        self.channel_names = channel_names
        # Ensure deep copy of multipliers to avoid direct mutation before signal
        self.current_multipliers = current_multipliers.copy()
        
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
        header_layout.addWidget(QLabel("Amplitude (%)"))
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
            
            # Current value (float 1.0 -> 100%)
            val_float = self.current_multipliers.get(i, 1.0)
            val_percent = int(val_float * 100.0)
            
            # Slider (0 to 200%)
            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, 200)
            slider.setValue(val_percent)
            slider.valueChanged.connect(lambda val, idx=i: self.on_slider_changed(val, idx))
            row_layout.addWidget(slider)
            
            # SpinBox (0 to 200%)
            spin = QDoubleSpinBox()
            spin.setRange(0, 200)
            spin.setSingleStep(1)
            spin.setDecimals(1) # Allow 0.1% precision if needed, but slider is int
            spin.setValue(val_percent)
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
        # val is int (%)
        # Update spinbox without triggering signal loop
        spin = self.spinboxes[idx]
        spin.blockSignals(True)
        spin.setValue(float(val))
        spin.blockSignals(False)
        
        self.update_multiplier(idx, val)
        
    def on_spin_changed(self, val, idx):
        # val is float (%)
        val_int = int(val)
        
        # Update slider
        slider = self.sliders[idx]
        slider.blockSignals(True)
        slider.setValue(val_int)
        slider.blockSignals(False)
        
        self.update_multiplier(idx, val)
        
    def update_multiplier(self, idx, val_percent):
        # Convert % -> float for the backend
        val_float = val_percent / 100.0
        self.current_multipliers[idx] = val_float
        self.amplitude_changed.emit(self.current_multipliers)
