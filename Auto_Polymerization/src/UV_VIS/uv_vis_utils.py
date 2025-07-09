"""
UV-VIS Spectroscopy Utilities Module

This module provides robust, maintainable tools for UV-VIS spectroscopy data acquisition, processing,
and analysis in automated polymerization workflows. It includes functions for spectrum
acquisition, baseline correction, absorbance calculation, and conversion analysis, with a focus on
centralized logic, error handling, and code clarity.

Key Features:
    - Automated spectrum acquisition using CCS200 spectrometer
    - Centralized filename and timestamp generation for all saved data
    - Baseline correction for all spectra in a folder
    - Absorbance calculation using baseline as reference
    - Conversion analysis at specific wavelengths (e.g., 520 nm)
    - Batch processing of multiple spectrum files
    - Automatic file organization and naming conventions using constants
    - Robust file loading with automatic encoding correction (UTF-8/UTF-16)
    - Centralized logging for all operations (using Python's logging module)
    - DRY (Don't Repeat Yourself) principles throughout
    - Type hints and detailed docstrings for all public functions
    - Error handling and informative warnings for missing/corrupt data

Spectrum Types Supported:
    - Baseline spectra: Reference spectra for background correction
    - t0 spectra: Initial time point spectra for conversion calculations
    - Regular spectra: Sample spectra for analysis
    - Corrected spectra: Baseline-subtracted spectra
    - Absorbance spectra: Calculated absorbance values

File Naming Conventions:
    - Baseline: {timestamp}_UV_VIS_baseline_spectrum.txt
    - t0: {timestamp}_UV_VIS_t0_spectrum.txt
    - Regular: {timestamp}_UV_VIS_spectrum.txt
    - Corrected: {base_name}_corrected.txt
    - Absorbance: {base_name}_absorbance.txt
    - Conversion: conversion_{base_name}.txt

Data Format:
    All spectrum files are saved as tab-separated text files with header:
    "Wavelength (nm)\tIntensity (a.u.)" or "Wavelength (nm)\tAbsorbance (a.u.)"

Dependencies:
    - numpy: For numerical operations and array handling
    - matterlab_spectrometers: For spectrometer communication
    - pathlib: For cross-platform path handling
    - glob: For file pattern matching
    - logging: For robust, configurable logging

Hardware Requirements:
    - CCS200 spectrometer (USB connection)
    - Device ID: M00479664
    - Default integration time: 3 ms

Usage Example:
    # Take a baseline spectrum
    spectrum, wavelengths, filename, _ = take_spectrum(baseline=True)
    
    # Take a t0 spectrum
    spectrum, wavelengths, filename, _ = take_spectrum(t0=True)
    
    # Take regular sample spectra
    spectrum, wavelengths, filename, _ = take_spectrum()
    
    # Process all spectra (baseline correction)
    corrected_data = subtract_baseline_from_spectra()
    
    # Calculate absorbance for all corrected spectra
    absorbance_data = calculate_absorbance()
    
    # Calculate conversion at 520 nm
    conversion_data = calculate_conversion_at_520nm()

Author: Michael Ringleb (with help from cursor.ai)
Date: [08.07.2025]
Version: 0.3
"""

import logging
import numpy as np
from pathlib import Path
from datetime import datetime
import glob

# Set up module-level logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Change to DEBUG for more verbosity

# Magic strings for spectrum types and patterns
PATTERN_BASELINE = "baseline"
PATTERN_T0 = "t0"
PATTERN_ABSORBANCE = "absorbance"
PATTERN_CORRECTED = "corrected"
# Correct path to the data folder, relative to the project root
DATA_FOLDER = "users/data/UV_VIS_data"
TARGET_WAVELENGTH = 520  # nm


def get_timestamp():
    """
    Get the current timestamp as a string for filenames.
    
    Returns:
        str: Timestamp in the format YYYY-MM-DD_HH-MM-SS
    """
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def generate_filename(spectrum_type, timestamp=None, base_name=None):
    """
    Generate a standardized filename for spectrum files.
    
    Args:
        spectrum_type (str): Type of spectrum ('baseline', 't0', 'absorbance', 'corrected', 'spectrum', etc.)
        timestamp (str, optional): Timestamp string. If None, will generate a new one.
        base_name (str, optional): Base name for corrected/absorbance files.
    
    Returns:
        str: Generated filename.
    """
    if timestamp is None:
        timestamp = get_timestamp()
    if spectrum_type == PATTERN_BASELINE:
        return f"{timestamp}_UV_VIS_baseline_spectrum.txt"
    elif spectrum_type == PATTERN_T0:
        return f"{timestamp}_UV_VIS_t0_spectrum.txt"
    elif spectrum_type == PATTERN_ABSORBANCE:
        return f"{timestamp}_UV_VIS_absorbance_spectrum.txt"
    elif spectrum_type == PATTERN_CORRECTED and base_name:
        return f"{base_name}_corrected.txt"
    elif spectrum_type == "absorbance_file" and base_name:
        return f"{base_name}_absorbance.txt"
    elif spectrum_type == "conversion" and base_name:
        return f"conversion_{base_name}.txt"
    else:
        return f"{timestamp}_UV_VIS_spectrum.txt"


def get_spectra_path(data_folder=DATA_FOLDER):
    """
    Get the absolute path to the spectra data folder.
    Args:
        data_folder (str): Relative path to the spectra folder.
    Returns:
        Path: Path object to the spectra directory.
    """
    # This assumes this file is in Auto_Polymerization/src/UV_VIS/
    # and the project root is two levels up
    return Path(__file__).resolve().parents[2] / data_folder


def find_files_by_pattern(spectra_path, pattern):
    """
    Find files containing a specific pattern using numpy operations.
    
    Args:
        spectra_path (Path): Path object to the spectra directory.
        pattern (str): Substring to search for in filenames.
    
    Returns:
        np.ndarray: Array of matching file paths.
    """
    files = np.array(list(spectra_path.glob("*.txt")))
    if len(files) == 0:
        return np.array([])
    mask = np.char.find(files.astype(str), pattern) >= 0
    return files[mask]


def load_spectrum_data(file_path):
    """
    Load spectrum data from file, handling UTF-8 and UTF-16 encodings.
    If the file is UTF-16, it will be converted to UTF-8 and re-saved.
    
    Args:
        file_path (str or Path): Path to the spectrum file.
    
    Returns:
        np.ndarray or None: Loaded data as a 2D numpy array, or None if loading fails.
    """
    try:
        return np.loadtxt(file_path, skiprows=1)
    except Exception as e_utf8:
        try:
            with open(file_path, "r", encoding="utf-16") as fin:
                lines = fin.readlines()
            # Remove BOM if present
            if lines and lines[0].startswith('\ufeff'):
                lines[0] = lines[0][1:]
            # Save as UTF-8
            with open(file_path, "w", encoding="utf-8") as fout:
                fout.writelines(lines)
            logger.warning(f"File {file_path} was in UTF-16 and has been converted to UTF-8.")
            return np.loadtxt(file_path, skiprows=1)
        except Exception as e_utf16:
            logger.error(f"Error loading {file_path}: {e_utf16}")
            return None


def save_spectrum(wavelengths, spectrum, timestamp, filename=None, baseline=False, t0=False, absorbance=False):
    """
    Save spectrum data to users/data/UV_VIS_data folder with automatic type detection.
    
    Args:
        wavelengths (np.ndarray): Array of wavelength values.
        spectrum (np.ndarray): Array of intensity/absorbance values.
        timestamp (str): Timestamp string for filename.
        filename (str, optional): Optional filename. If None, generates timestamp-based name.
        baseline (bool): True if this is a baseline spectrum.
        t0 (bool): True if this is a t0 spectrum.
        absorbance (bool): True if this is an absorbance spectrum.
    
    Returns:
        Path: Path to the saved file.
    """
    spectra_folder = get_spectra_path()
    spectra_folder.mkdir(parents=True, exist_ok=True)
    if filename is None:
        if baseline:
            filename = generate_filename(spectrum_type=PATTERN_BASELINE, timestamp=timestamp)
        elif t0:
            filename = generate_filename(spectrum_type=PATTERN_T0, timestamp=timestamp)
        elif absorbance:
            filename = generate_filename(spectrum_type=PATTERN_ABSORBANCE, timestamp=timestamp)
        else:
            filename = generate_filename(spectrum_type="spectrum", timestamp=timestamp)
    file_path = spectra_folder / filename
    data = np.column_stack((wavelengths, spectrum))
    np.savetxt(file_path, data, header="Wavelength (nm)\tIntensity (a.u.)", fmt="%.4f\t%.6f")
    logger.info(f"Spectrum saved to {file_path}")
    return file_path


def take_spectrum(baseline=False, t0=False, calculate_conversion=False, integration_time=0.003):
    """
    Take a spectrum using the spectrometer and save it with appropriate naming.
    Optionally, calculate conversion from the latest absorbance data.
    
    Args:
        baseline (bool): True if this is a baseline spectrum.
        t0 (bool): True if this is a t0 spectrum.
        calculate_conversion (bool): True to calculate conversion from latest spectrum.
        integration_time (float): Integration time for the spectrometer in seconds.
    
    Returns:
        tuple: (spectrum_data, wavelengths, filename, conversion_value)
            spectrum_data (np.ndarray): Measured spectrum values.
            wavelengths (np.ndarray): Wavelength values.
            filename (str): Name of the saved file.
            conversion_value (float or None): Conversion value if calculated, else None.
    """
    spec = get_spectrometer()
    spectrum = spec.measure_spectrum(integration_time)
    wavelengths = spec.get_wavelength_data()
    timestamp = get_timestamp()
    if baseline:
        filename = generate_filename(spectrum_type=PATTERN_BASELINE, timestamp=timestamp)
    elif t0:
        filename = generate_filename(spectrum_type=PATTERN_T0, timestamp=timestamp)
    else:
        filename = generate_filename(spectrum_type="spectrum", timestamp=timestamp)
    save_spectrum(wavelengths, spectrum, timestamp, filename, baseline, t0)
    conversion_value = None
    if calculate_conversion and not baseline and not t0:
        subtract_baseline_from_spectra()
        calculate_absorbance()
        conversion_data = calculate_conversion_at_520nm()
        if conversion_data and 'conversions' in conversion_data:
            conversion_value = conversion_data['conversions'][-1] if conversion_data['conversions'] else None
    return spectrum, wavelengths, filename, conversion_value


def filter_spectra_files(spectra_path, include_patterns=None, exclude_patterns=None):
    """
    Return a list of .txt files in spectra_path that include all specified substrings and exclude all others.

    Args:
        spectra_path (Path): Path to the spectra directory.
        include_patterns (list of str, optional): Each pattern must be present in the filename.
        exclude_patterns (list of str, optional): Each pattern must NOT be present in the filename.

    Returns:
        np.ndarray: Array of Path objects matching the criteria.
    """
    files = np.array(list(spectra_path.glob("*.txt")))
    mask = np.ones(len(files), dtype=bool)
    if include_patterns:
        for pat in include_patterns:
            mask &= np.char.find(files.astype(str), pat) >= 0
    if exclude_patterns:
        for pat in exclude_patterns:
            mask &= np.char.find(files.astype(str), pat) < 0
    return files[mask]


def get_baseline_intensities(spectra_path, shape):
    """
    Get baseline intensities from the first baseline file in the directory, or return zeros if not found.

    Args:
        spectra_path (Path): Path to the spectra directory.
        shape (tuple): Shape of the intensity array to match (e.g., (N,)).

    Returns:
        np.ndarray: Baseline intensities array, or zeros if no baseline file is found.
    """
    baseline_files = find_files_by_pattern(spectra_path, PATTERN_BASELINE)
    if len(baseline_files) > 0:
        baseline_data = load_spectrum_data(baseline_files[0])
        if baseline_data is not None:
            return baseline_data[:, 1]
    return np.zeros(shape)


def process_spectra_files(operation_func, data_folder=DATA_FOLDER, include_patterns=None, exclude_patterns=None, **kwargs):
    """
    Apply an operation function to all selected spectra files in a folder.

    Args:
        operation_func (callable): Function to apply to each spectrum file. Should accept (wavelengths, intensities, baseline_intensities, file, **kwargs).
        data_folder (str): Path to folder containing spectra files.
        include_patterns (list of str, optional): Only process files containing all these substrings.
        exclude_patterns (list of str, optional): Skip files containing any of these substrings.
        **kwargs: Additional arguments for the operation function.

    Returns:
        list: List of results from the operation function, one per processed file. List may be empty if no files match.
    """
    spectra_path = get_spectra_path(data_folder)
    files = filter_spectra_files(spectra_path, include_patterns, exclude_patterns)
    results = []
    for file in files:
        data = load_spectrum_data(file)
        if data is None:
            continue
        wavelengths = data[:, 0]
        intensities = data[:, 1]
        baseline_intensities = get_baseline_intensities(spectra_path, intensities.shape)
        result = operation_func(wavelengths, intensities, baseline_intensities, file, **kwargs)
        results.append(result)
    return results


def subtract_baseline_operation(wavelengths, intensities, baseline_intensities, file, **kwargs):
    """
    Operation function for baseline subtraction.
    
    Args:
        wavelengths (np.ndarray): Wavelength values.
        intensities (np.ndarray): Intensity values.
        baseline_intensities (np.ndarray): Baseline intensity values.
        file (Path): Original file path.
    
    Returns:
        np.ndarray: Corrected data as a 2D array.
    """
    corrected_intensities = intensities - baseline_intensities
    base_name = Path(file).stem
    output_filename = generate_filename(spectrum_type=PATTERN_CORRECTED, base_name=base_name)
    timestamp = get_timestamp()
    save_spectrum(wavelengths, corrected_intensities, timestamp, output_filename)
    return np.column_stack((wavelengths, corrected_intensities))


def calculate_absorbance_operation(wavelengths, intensities, baseline_intensities, file, **kwargs):
    """
    Operation function for absorbance calculation.
    
    Args:
        wavelengths (np.ndarray): Wavelength values.
        intensities (np.ndarray): Intensity values.
        baseline_intensities (np.ndarray): Baseline intensity values.
        file (Path): Original file path.
    
    Returns:
        np.ndarray: Absorbance data as a 2D array.
    """
    reference_intensities = np.where(baseline_intensities <= 0, 1e-10, baseline_intensities)
    absorbance = -np.log10(intensities / reference_intensities)
    base_name = Path(file).stem
    if base_name.endswith(f"_{PATTERN_CORRECTED}"):
        base_name = base_name[:-(len(PATTERN_CORRECTED)+1)]
    output_filename = generate_filename(spectrum_type="absorbance_file", base_name=base_name)
    timestamp = get_timestamp()
    save_spectrum(wavelengths, absorbance, timestamp, output_filename, absorbance=True)
    return np.column_stack((wavelengths, absorbance))


def subtract_baseline_from_spectra(data_folder=DATA_FOLDER):
    """
    Subtract baseline from all spectra in the specified folder.

    Only processes files that do NOT already have 'corrected' or 'absorbance' in the filename.
    File selection is handled by filter_spectra_files.

    Args:
        data_folder (str): Path to folder containing spectra files.

    Returns:
        list: List of corrected spectra data arrays, one per processed file. List may be empty if no files match.
    """
    return process_spectra_files(
        subtract_baseline_operation,
        data_folder,
        include_patterns=None,
        exclude_patterns=[PATTERN_CORRECTED, PATTERN_ABSORBANCE]
    )


def calculate_absorbance(data_folder=DATA_FOLDER):
    """
    Calculate absorbance for all corrected spectra in the specified folder.

    Only processes files with 'corrected' in the filename and skips those already containing 'absorbance'.
    File selection is handled by filter_spectra_files.

    Args:
        data_folder (str): Path to folder containing corrected spectra files.

    Returns:
        list: List of absorbance data arrays, one per processed file. List may be empty if no files match.
    """
    return process_spectra_files(
        calculate_absorbance_operation,
        data_folder,
        include_patterns=[PATTERN_CORRECTED],
        exclude_patterns=[PATTERN_ABSORBANCE]
    )


def calculate_conversion_at_520nm(data_folder=DATA_FOLDER):
    """
    Calculate conversion at 520 nm from absorbance spectra.
    Conversion = 1 - (absorbance of spectrum) / (absorbance of t0)
    
    Args:
        data_folder (str): Path to folder containing absorbance files.
    
    Returns:
        dict: Dictionary containing:
            - timestamps: List of timestamps for each spectrum
            - absorbances: List of absorbance values at target wavelength
            - conversions: List of conversion values (1 - absorbance/t0_absorbance)
            - t0_absorbance: Reference absorbance value from t0 spectrum
            - wavelength: Actual wavelength used (closest to 520 nm)
    """
    spectra_path = get_spectra_path(data_folder)
    absorbance_files = find_files_by_pattern(spectra_path, PATTERN_ABSORBANCE)
    if len(absorbance_files) == 0:
        logger.warning("No absorbance files found!")
        return {}
    t0_files = find_files_by_pattern(spectra_path, PATTERN_T0)
    if len(t0_files) == 0:
        logger.warning("No t0 absorbance file found!")
        return {}
    t0_file = t0_files[0]
    t0_data = load_spectrum_data(t0_file)
    if t0_data is None:
        return {}
    t0_wavelengths = t0_data[:, 0]
    t0_absorbances = t0_data[:, 1]
    wavelength_idx = np.argmin(np.abs(t0_wavelengths - TARGET_WAVELENGTH))
    t0_absorbance_target = t0_absorbances[wavelength_idx]
    actual_wavelength = t0_wavelengths[wavelength_idx]
    logger.info(f"Using absorbance at {actual_wavelength:.1f} nm (closest to {TARGET_WAVELENGTH} nm)")
    logger.info(f"t0 absorbance: {t0_absorbance_target:.6f}")
    t0_mask = np.char.find(absorbance_files.astype(str), PATTERN_T0) >= 0
    process_mask = ~t0_mask
    files_to_process = absorbance_files[process_mask]
    conversion_data = []
    for file in files_to_process:
        spectrum_data = load_spectrum_data(file)
        if spectrum_data is None:
            continue
        wavelengths = spectrum_data[:, 0]
        absorbances = spectrum_data[:, 1]
        if not np.array_equal(wavelengths, t0_wavelengths):
            logger.warning(f"Warning: Wavelength mismatch in {file}")
            continue
        absorbance_target = absorbances[wavelength_idx]
        if t0_absorbance_target > 0:
            conversion = 1 - (absorbance_target / t0_absorbance_target)
        else:
            logger.warning(f"Warning: t0 absorbance at {actual_wavelength:.1f} nm is zero or negative")
            conversion = 0
        timestamp = extract_timestamp(Path(file).stem)
        conversion_data.append({
            'timestamp': timestamp,
            'absorbance': absorbance_target,
            'conversion': conversion,
            'file': file
        })
    conversion_data.sort(key=lambda x: x['timestamp'])
    if conversion_data:
        timestamp_save = get_timestamp()
        conversion_filename = generate_filename(spectrum_type="conversion", base_name=f"at_{actual_wavelength:.0f}nm_{timestamp_save}")
        file_path = spectra_path / conversion_filename
        data_array = np.array([[d['timestamp'], d['absorbance'], d['conversion']] 
                              for d in conversion_data])
        np.savetxt(file_path, data_array, 
                   header="Timestamp\tAbsorbance\tConversion", 
                   fmt="%s\t%.6f\t%.6f")
        logger.info(f"Conversion data saved to {file_path}")
    return {
        'timestamps': [d['timestamp'] for d in conversion_data],
        'absorbances': [d['absorbance'] for d in conversion_data],
        'conversions': [d['conversion'] for d in conversion_data],
        't0_absorbance': t0_absorbance_target,
        'wavelength': actual_wavelength
    }


def extract_timestamp(filename_stem):
    """
    Extract timestamp from a filename stem.
    
    Args:
        filename_stem (str): The stem of the filename (without extension).
    
    Returns:
        str: Extracted timestamp or 'unknown' if not found.
    """
    import re
    match = re.search(r'(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})', filename_stem)
    return match.group(1) if match else "unknown"


def get_spectrometer():
    """
    Get an instance of the CCS200 spectrometer.
    
    Returns:
        CCSSpectrometer: Instance of the spectrometer.
    """
    from matterlab_spectrometers.ccs_spectrometer import CCSSpectrometer
    return CCSSpectrometer(
        usb_port="USB",
        device_model="CCS200",
        device_id="M00479664"
    )


