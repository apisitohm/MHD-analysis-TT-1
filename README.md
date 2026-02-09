# MHD Analysis Program

## Overview

The MHD Analysis Program is a sophisticated Python-based tool designed for the analysis and visualization of Magnetohydrodynamics (MHD) data from tokamak experiments (specifically Thailand Tokamak 1). It provides a comprehensive suite of tools for signal processing, including spectrogram analysis, wavelet transforms, Singular Value Decomposition (SVD), and phase difference calculations.

Built with **PySide6** for a modern, responsive user interface and **NumPy/SciPy** for robust numerical computation, this application enables researchers to:

*   Load shot data from local files or remote MDSplus servers.
*   Analyze Magnetic m (poloidal mode number) and n (toroidal mode number) modes.
*   Visualize time-frequency domains using Spectrograms and Wavelets.
*   Compute and visualize spatial structures and phase differences.
*   Export high-quality reports in PDF and Image formats.

## Features

*   **Data Acquisition**: Seamless loading from MDSplus trees or local text files.
*   **Advanced Signal Processing**:
    *   **Spectrogram**: Short-Time Fourier Transform (STFT) visualization.
    *   **Wavelet Analysis**: Time-localized frequency analysis.
    *   **SVD**: Decomposition of signals into spatial and temporal modes.
    *   **Phase Analysis**: Calculation of phase differences between coils.
*   **Interactive UI**: Zoom, pan, and cursor tracking across synchronized plots.
*   **Export Capabilities**: Generate professional PDF reports or high-resolution PNG snapshots of analysis results.
*   **Configuration**: Flexible `config.json` for tuning analysis parameters (filters, thresholds).

## Requirements

*   Python 3.8+
*   See `requirements.txt` for a full list of dependencies.

## Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/apisitohm/MHD-analysis-TT-1.git
    cd MHD-analysis-TT-1
    ```

2.  **Create a virtual environment** (Recommended):
    ```bash
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # Linux/Mac
    source venv/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

To start the application, run the main entry point:

```bash
python run.py
```

### Basic Workflow
1.  **Load Data**: Enter a Shot Number in the top panel and click **Load**. ensure your method (MDSplus or Local) is selected correctly.
2.  **Select Mode**: Choose between available modes (e.g., Poloidal/Toroidal Analysis).
3.  **Analyze**:
    *   Use the **Spectrogram** tab to view frequency content over time.
    *   Select a time range to view **Wavelet** details.
    *   Inspect **SVD** modes to understand spatial structures.
4.  **Export**: Click the **Export** button to save your current analysis as a PDF report.

## Configuration

The application uses `config.json` and `params.json` to store settings.
*   `config.json`: Stores application-wide settings like default paths and export preferences.
*   `params.json`: Stores analysis-specific parameters (e.g., default frequency ranges).

## Project Structure

*   `run.py`: Application entry point.
*   `src/`: Source code directory.
    *   `ui/`: PySide6 widgets and main window logic.
    *   `data/`: Data loading (MDSplus/Text) and signal processing algorithms (SVD, FFT).
    *   `utils/`: Helper utilities for configuration and exporting.
*   `tests/`: Unit and benchmark tests.

## Contributing

Please see [DEVELOPMENT.md](DEVELOPMENT.md) for details on how to set up your development environment and contribute to this project.

## License

[MIT License](LICENSE) (or specify your license)
