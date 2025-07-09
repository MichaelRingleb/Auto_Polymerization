"""
Test suite for UV-VIS utility functions.

This script provides basic functional tests for the main features of uv_vis_utils.py,
including baseline subtraction, absorbance calculation, conversion calculation, spectrum acquisition, and plotting.
It also includes a diagnostic function to help debug file discovery issues.

Usage:
    python test_uv_vis_utils.py

Requirements:
    - Place this script in the same directory as uv_vis_utils.py or ensure it is on the Python path.
    - Ensure your data folder (see DATA_FOLDER in uv_vis_utils.py) contains appropriate test spectra.
    - For take_spectrum test, hardware must be connected (or simulate with baseline=True).

Tests:
    - Baseline subtraction
    - Absorbance calculation
    - Conversion calculation at 520 nm
    - Spectrum acquisition (take_spectrum)
    - Plotting the first absorbance spectrum
    - (Optional) Diagnostics for file discovery

Author: [Your Name]
Date: [Date]
"""

from uv_vis_utils import (
    subtract_baseline_from_spectra,
    calculate_absorbance,
    calculate_conversion_at_520nm,
    get_spectra_path,
    find_files_by_pattern,
    load_spectrum_data,
    take_spectrum,
    DATA_FOLDER
)
import numpy as np
import logging
import matplotlib.pyplot as plt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_subtract_baseline():
    logger.info("Testing baseline subtraction...")
    results = subtract_baseline_from_spectra()
    if results:
        logger.info(f"Baseline subtraction successful for {len(results)} spectra.")
    else:
        logger.warning("Baseline subtraction failed or no spectra found.")

def test_calculate_absorbance():
    logger.info("Testing absorbance calculation...")
    results = calculate_absorbance()
    if results:
        logger.info(f"Absorbance calculation successful for {len(results)} spectra.")
    else:
        logger.warning("Absorbance calculation failed or no spectra found.")

def test_calculate_conversion():
    logger.info("Testing conversion calculation at 520 nm...")
    results = calculate_conversion_at_520nm()
    if results and 'conversions' in results:
        logger.info(f"Conversion calculation successful for {len(results['conversions'])} spectra.")
        logger.info(f"Sample conversions: {results['conversions']}")
    else:
        logger.warning("Conversion calculation failed or no absorbance spectra found.")

def test_take_spectrum():
    logger.info("Testing spectrum acquisition (take_spectrum)...")
    try:
        spectrum, wavelengths, filename, conversion = take_spectrum(baseline=True)
        if spectrum is not None and wavelengths is not None:
            logger.info(f"Spectrum acquired and saved as {filename}.")
            logger.info(f"Spectrum shape: {spectrum.shape}, Wavelengths shape: {wavelengths.shape}")
            if conversion is not None:
                logger.info(f"Conversion value: {conversion}")
        else:
            logger.warning("Spectrum acquisition returned None values.")
    except Exception as e:
        logger.error(f"Error during spectrum acquisition: {e}")

def test_plot_first_absorbance():
    logger.info("Testing plotting of first absorbance spectrum...")
    spectra_path = get_spectra_path()
    absorbance_files = find_files_by_pattern(spectra_path, 'absorbance')
    if len(absorbance_files) > 0:
        data = load_spectrum_data(absorbance_files[0])
        if data is not None:
            wavelengths = data[:, 0]
            absorbance = data[:, 1]
            plt.figure()
            plt.plot(wavelengths, absorbance)
            plt.xlabel("Wavelength (nm)")
            plt.ylabel("Absorbance (a.u.)")
            plt.title("First Absorbance Spectrum")
            plt.grid(True)
            plt.show(block=False)
            logger.info("Plot displayed for first absorbance spectrum.")
        else:
            logger.warning("Failed to load first absorbance spectrum.")
    else:
        logger.warning("No absorbance spectra found for plotting.")

def debug_spectra_folder(data_folder=DATA_FOLDER):
    """
    Print diagnostics about the spectra folder and file discovery.
    """
    path = get_spectra_path(data_folder)
    logger.info(f"Looking for spectra in: {path}")
    logger.info(f"Path exists: {path.exists()}")
    logger.info(f"All files: {list(path.glob('*'))}")
    txt_files = list(path.glob("*.txt"))
    logger.info(f"All .txt files: {txt_files}")
    for pattern in ["baseline", "t0", "absorbance", "corrected"]:
        files = np.array([str(f) for f in txt_files])
        mask = np.char.find(files.astype(str), pattern) >= 0
        logger.info(f"Files matching '{pattern}': {files[mask]}")

if __name__ == "__main__":
    test_subtract_baseline()
    test_calculate_absorbance()
    test_calculate_conversion()
    test_take_spectrum()
    test_plot_first_absorbance()
    # Uncomment the next line if you want to run diagnostics
    #debug_spectra_folder()