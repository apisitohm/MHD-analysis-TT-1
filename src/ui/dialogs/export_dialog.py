# src/ui/dialogs/export_dialog.py
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QCheckBox, QComboBox, QLineEdit, QPushButton, 
                            QGroupBox, QFileDialog, QFormLayout, QScrollArea, QWidget)
from PySide6.QtCore import Qt
import os

class ExportDialog(QDialog):
    def __init__(self, shot_no, mode, type_str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Export Results - Shot {shot_no}")
        self.resize(500, 650)
        
        self.shot_no = shot_no
        self.mode = mode
        self.type_str = type_str
        
        # Result Dictionary to return
        self.selected_options = {}
        self.export_format = "Image"
        self.export_path = ""
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 1. Info Header
        info_group = QGroupBox("Experiment Info")
        info_layout = QHBoxLayout(info_group)
        info_layout.addWidget(QLabel(f"Shot: <b>{self.shot_no}</b>"))
        info_layout.addWidget(QLabel(f"Mode: <b>{self.mode}</b>"))
        info_layout.addWidget(QLabel(f"Type: <b>{self.type_str}</b>"))
        layout.addWidget(info_group)
        
        # 2. Checkboxes (Scrollable if needed, but fixed list is small enough)
        cb_group = QGroupBox("Select Results to Export")
        cb_layout = QVBoxLayout(cb_group)
        
        self.checkboxes = {}
        
        # Define items with their internal keys
        items = [
            ("spectrogram", "Spectrogram"),
            ("wavelet", "Wavelet"),
            ("wavelet_peaks_phase_diff", "Wavelet Peaks (Phase Diff)"),
            ("phase_diff_coil", "Phase Diff vs Coil Loc"),
            ("wavelet_peaks_phase_cycle", "Wavelet Peaks (Phase Cycle)"),
            ("phase_cycle", "Phase Cycle"),
            ("singular_values", "Singular Values"),
            ("spatial_structure", "Spatial Structure"),
            ("init_phase_table", "Init Phase Table"),
            ("amp_signal_table", "Amp Signal Table")
        ]
        
        for key, label in items:
            cb = QCheckBox(label)
            cb.setChecked(True) # Default Select All
            self.checkboxes[key] = cb
            cb_layout.addWidget(cb)
            
        layout.addWidget(cb_group)
        
        # 3. Format Selection
        fmt_group = QGroupBox("Export Format")
        fmt_layout = QHBoxLayout(fmt_group)
        self.combo_fmt = QComboBox()
        self.combo_fmt.addItems(["Image (.png)", "PDF Report (.pdf)"])
        self.combo_fmt.currentTextChanged.connect(self.on_fmt_changed)
        fmt_layout.addWidget(QLabel("Format:"))
        fmt_layout.addWidget(self.combo_fmt)
        layout.addWidget(fmt_group)
        
        # 4. Path Selection
        path_group = QGroupBox("Export Path")
        path_layout = QHBoxLayout(path_group)
        
        self.txt_path = QLineEdit()
        self.txt_path.setText(os.path.join(os.getcwd(), "Exports")) # Default
        path_layout.addWidget(self.txt_path)
        
        btn_browse = QPushButton("Browse")
        btn_browse.clicked.connect(self.on_browse)
        path_layout.addWidget(btn_browse)
        
        layout.addWidget(path_group)
        
        layout.addStretch()
        
        # 5. Buttons
        btn_layout = QHBoxLayout()
        self.lbl_status = QLabel("")
        btn_layout.addWidget(self.lbl_status)
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        
        btn_export = QPushButton("Export")
        btn_export.setObjectName("btn_export") # For styling if needed
        btn_export.setStyleSheet("background-color: #007acc; color: white; font-weight: bold; padding: 6px 20px;")
        btn_export.clicked.connect(self.on_export)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_export)
        
        layout.addLayout(btn_layout)
        
    def on_fmt_changed(self, text):
        self.export_format = text
        
    def on_browse(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Export Directory", self.txt_path.text())
        if dir_path:
            self.txt_path.setText(dir_path)
            
    def on_export(self):
        # Validate logic
        path = self.txt_path.text()
        if not path:
            self.lbl_status.setText("<font color='red'>Please select a path</font>")
            return
            
        self.export_path = path
        
        # Gather checkboxes
        selection = []
        for key, cb in self.checkboxes.items():
            if cb.isChecked():
                selection.append(key)
        
        if not selection:
            self.lbl_status.setText("<font color='red'>Select at least one item</font>")
            return
            
        self.selected_options = {
            'format': 'pdf' if 'PDF' in self.combo_fmt.currentText() else 'image',
            'path': self.export_path,
            'items': selection
        }
        
        self.accept()
