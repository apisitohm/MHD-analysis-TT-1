
from PySide6.QtWidgets import QApplication
import sys
import numpy as np
import pyqtgraph as pg

# Add src to path
import os
sys.path.append(r'd:\TT1\MHD program')

from src.ui.widgets.wavelet_widget import WaveletWidget

def test_wavelet_smoothing():
    app = QApplication(sys.argv)
    
    widget = WaveletWidget()
    widget.show()
    
    # Create dummy data
    # 1000 time points, 12 channels
    time_array = np.linspace(0, 100, 1000)
    data_matrix = np.random.rand(1000, 12)
    
    print("Calling update_plot...")
    widget.update_plot(time_array, data_matrix)
    print("update_plot finished successfully.")
    
    # Check if image data shape is zoomed
    img_data = widget.img_item.image
    print(f"Original shape: {data_matrix.shape}")
    print(f"Smoothed shape: {img_data.shape}")
    
    expected_shape = (1000, 120) 
    
    if img_data.shape == expected_shape:
        print("SUCCESS: Shape matches expected 10x upsampling.")
    else:
        print(f"WARNING: Shape mismatch. Expected {expected_shape}, got {img_data.shape}")

    # app.exec()
    app.quit()

if __name__ == "__main__":
    test_wavelet_smoothing()
