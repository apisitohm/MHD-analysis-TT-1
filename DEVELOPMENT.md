# Development Guide

This document provides instructions for developers who want to contribute to the MHD Analysis Program or modify it for their own use.

## Environment Setup

1.  **Python Version**: Ensure you are using Python 3.8 (for me used 3.11.14) or higher.
2.  **Virtual Environment**: Always work within a virtual environment to manage dependencies locally.
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```
3.  **Dependencies**: Install development dependencies (if any) along with production requirements.
    ```bash
    pip install -r requirements.txt
    ```

## Project Architecture

The project follows a modular architecture separating UI, Data Logic, and Utilities.

### `src/ui/`
Contains all PySide6 widgets.
*   `main_window.py`: The main application window and layout orchestration.
*   `widgets/`: Reusable custom widgets (e.g., plotters, control panels).
*   `dialogs/`: Popup dialogs for settings and exports.

### `src/data/`
Handles data retrieval and mathematical processing.
*   `loader.py`: Interfaces for fetching data from Text files or MDSplus.
    *   If you need to add a new data source, implement a new function here and update `fetch_mhd_data`.
*   `analysis.py`: Core signal processing library.
    *   **SignalProcessor**: Static class containing methods for SVD, Spectrogram, Wavelet, and Phase calculations.
    *   Dependency on `scipy.signal` and `numpy`.

### `src/utils/`
*   `config_manager.py`: Singleton for managing `config.json`.
*   `export_manager.py`: Handles PDF generation using `reportlab`.

## Key Libraries

*   **PySide6**: Used for the GUI. Familiarity with Qt slots/signals is essential.
*   **PyQtGraph**: Used for high-performance plotting (Spectrograms, line plots). It is faster than Matplotlib for real-time interaction.
*   **MDSthin**: A lightweight client for MDSplus data access.

## Running Tests

Tests are located in the `tests/` directory.

To run tests:
```bash
python -m unittest discover tests
```

or for specific benchmark scripts:
```bash
python tests/benchmark_modules.py
```

## Adding New Features

### Adding a New Analysis Plot
1.  **Update `analysis.py`**: Add the mathematical function in `SignalProcessor`.
2.  **Create Widget**: Create a new widget in `src/ui/widgets/` that uses `pyqtgraph` to display the data.
3.  **Update `MainWindow`**: Add the widget to the layout in `src/ui/main_window.py` and connect it to the data updates.

### Modifying Export Format
*   Edit `src/utils/export_manager.py` to change how PDFs are generated or to add new export formats (e.g., Excel/CSV).

## Coding Standards

*   Follow PEP 8 for Python code style.
*   Ensure all new functions have docstrings explaining arguments and return values.
*   Keep UI logic separate from Data logic where possible.

