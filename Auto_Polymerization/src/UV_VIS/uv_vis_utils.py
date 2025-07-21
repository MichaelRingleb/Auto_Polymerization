"""
Auto_Polymerization UV-VIS Spectroscopy Utilities

This module provides comprehensive tools for UV-VIS spectroscopy data acquisition, processing,
and analysis in automated polymerization workflows. It includes functions for spectrum
acquisition, data preprocessing, absorbance calculation, and conversion analysis, with a focus on
centralized logic, error handling, and code clarity.

Key Features:
- Automated spectrum acquisition using CCS200 spectrometer
- Centralized filename and timestamp generation for all saved data
- Negative value removal as a preprocessing step
- Absorbance calculation using a reference spectrum
- Conversion analysis at specific wavelengths (e.g., 520 nm)
- Batch processing of multiple spectrum files with duplicate detection
- Automatic file organization and naming conventions using constants
- Robust file loading with automatic encoding correction (UTF-8/UTF-16)
- Centralized logging for all operations (using Python's logging module)
- DRY (Don't Repeat Yourself) principles throughout
- Type hints and detailed docstrings for all public functions
- Error handling and informative warnings for missing/corrupt data
- Reaction completion detection based on absorbance stability

Spectrum Types Supported:
- Reference spectra: Reference spectra for absorbance calculation
- t0 spectra: Initial time point spectra for conversion calculations
- Regular spectra: Sample spectra for analysis
- Absorbance spectra: Calculated absorbance values

File Naming Conventions:
- Reference: {timestamp}_UV_VIS_reference_spectrum.txt
- t0: {timestamp}_UV_VIS_t0_spectrum.txt
- Regular: {timestamp}_UV_VIS_spectrum.txt
- Negative-removed: {base_name}_neg_removed.txt
- Absorbance: {base_name}_absorbance.txt
- Conversion: conversion_values.txt

Data Format:
All spectrum files are saved as tab-separated text files with header:
"Wavelength (nm)\tIntensity (a.u.)" or "Wavelength (nm)\tAbsorbance (a.u.)"

Hardware Requirements:
- CCS200 spectrometer (USB connection)
- Device ID: M00479664
- Default integration time: 3 ms

Dependencies:
- numpy: For numerical operations and array handling
- matterlab_spectrometers: For spectrometer communication
- pathlib: For cross-platform path handling
- logging: For robust, configurable logging
- re: For timestamp extraction from filenames

Usage Example:
    # Take a reference spectrum
    spectrum, wavelengths, filename, _, _ = take_spectrum(reference=True)
    
    # Take a t0 spectrum
    spectrum, wavelengths, filename, _, _ = take_spectrum(t0=True)
    
    # Take regular sample spectra
    spectrum, wavelengths, filename, _, reaction_complete = take_spectrum()
    
    # Preprocess all spectra to remove negative values
    remove_negatives_from_spectra()
    
    # Calculate absorbance for all negative-removed spectra
    absorbance_data = calculate_absorbance()
    
    # Calculate conversion at 520 nm
    conversion_data = calculate_conversion_at_520nm()

Author: Michael Ringleb (with help from cursor.ai)
Date: [Current Date]
Version: 1.0
"""

import logging
import numpy as np
from pathlib import Path
from datetime import datetime
import glob
import re
from typing import Optional, List, Dict, Tuple, Union

# Set up module-level logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Change to DEBUG for more verbosity

# Magic strings for spectrum types and patterns
PATTERN_T0 = "t0"
PATTERN_ABSORBANCE = "absorbance"
PATTERN_REFERENCE = "reference"
PATTERN_NEG_REMOVED = "neg_removed"

# Constants
DATA_FOLDER = "users/data/UV_VIS_data"
TARGET_WAVELENGTH = 520  # nm
DEFAULT_INTEGRATION_TIME = 0.003  # seconds
DEFAULT_TOLERANCE_PERCENT = 1.0  # percentage
DEFAULT_NUM_MEASUREMENTS = 10
MIN_REFERENCE_INTENSITY = 1e-10  # minimum intensity to avoid divide by zero

# File headers
HEADER_INTENSITY = "Wavelength (nm)\tIntensity (a.u.)"
HEADER_ABSORBANCE = "Wavelength (nm)\tAbsorbance (a.u.)"
HEADER_CONVERSION = "Filename\tAbsorbance\tConversion from comparison of absorbance at 520 nm to t0-spectrum (%)\n"

# File format strings
FMT_SPECTRUM = "%.4f\t%.6f"


def get_timestamp() -> str:
    """
    Get the current timestamp as a string for filenames.
    
    Returns:
        str: Timestamp in the format YYYY-MM-DD_HH-MM-SS
    """
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def generate_filename(spectrum_type: str, timestamp: Optional[str] = None, base_name: Optional[str] = None) -> str:
    """
    Generate a standardized filename for spectrum files.
    
    Args:
        spectrum_type (str): Type of spectrum ('reference', 't0', 'absorbance', 'spectrum', etc.)
        timestamp (str, optional): Timestamp string. If None, will generate a new one.
        base_name (str, optional): Base name for absorbance files (currently unused).
    
    Returns:
        str: Generated filename.
    """
    if timestamp is None:
        timestamp = get_timestamp()
    if spectrum_type == PATTERN_REFERENCE:
        return f"{timestamp}_UV_VIS_reference_spectrum.txt"
    elif spectrum_type == PATTERN_T0:
        return f"{timestamp}_UV_VIS_t0_spectrum.txt"
    elif spectrum_type == PATTERN_ABSORBANCE:
        return f"{timestamp}_UV_VIS_absorbance_spectrum.txt"
    else:
        return f"{timestamp}_UV_VIS_spectrum.txt"


def get_spectra_path(data_folder: str = DATA_FOLDER) -> Path:
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


def find_files_by_pattern(spectra_path: Path, pattern: str) -> np.ndarray:
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


def load_spectrum_data(file_path: Union[str, Path]) -> Optional[np.ndarray]:
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
            # Try UTF-16 with BOM
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
            try:
                # Try UTF-16 without BOM
                with open(file_path, "r", encoding="utf-16-le") as fin:
                    lines = fin.readlines()
                # Save as UTF-8
                with open(file_path, "w", encoding="utf-8") as fout:
                    fout.writelines(lines)
                logger.warning(f"File {file_path} was in UTF-16-LE and has been converted to UTF-8.")
                return np.loadtxt(file_path, skiprows=1)
            except Exception as e_utf16le:
                logger.error(f"Error loading {file_path}: {e_utf16le}")
                return None


def validate_spectrum_data(data: Optional[np.ndarray]) -> bool:
    """
    Validate that spectrum data is in the correct format.
    
    Args:
        data: Data to validate (usually from load_spectrum_data)
    
    Returns:
        bool: True if data is valid, False otherwise
    """
    return data is not None and data.ndim == 2 and data.shape[1] >= 2


def save_spectrum_file(file_path: Path, wavelengths: np.ndarray, values: np.ndarray, 
                      header: str, fmt: str = FMT_SPECTRUM) -> None:
    """
    Save spectrum data to file with consistent formatting.
    
    Args:
        file_path (Path): Path to save the file
        wavelengths (np.ndarray): Wavelength values
        values (np.ndarray): Intensity/absorbance values
        header (str): Header string for the file
        fmt (str): Format string for np.savetxt
    """
    np.savetxt(file_path, np.column_stack((wavelengths, values)),
               header=header, fmt=fmt)


def find_files_by_patterns(spectra_path: Path, include_patterns: Optional[List[str]] = None, 
                          exclude_patterns: Optional[List[str]] = None) -> List[Path]:
    """
    Find files matching include patterns and not matching exclude patterns.
    
    Args:
        spectra_path (Path): Path to search in
        include_patterns (list): Patterns that must be present in filename
        exclude_patterns (list): Patterns that must NOT be present in filename
    
    Returns:
        list: List of matching file paths
    """
    all_files = list(spectra_path.glob("*.txt"))
    
    if include_patterns:
        for pattern in include_patterns:
            all_files = [f for f in all_files if pattern in str(f)]
    
    if exclude_patterns:
        for pattern in exclude_patterns:
            all_files = [f for f in all_files if pattern not in str(f)]
    
    return all_files


def zero_negatives(array: np.ndarray) -> np.ndarray:
    """
    Return a copy of the array with all negative values set to zero.

    Args:
        array (np.ndarray): Input array.
    
    Returns:
        np.ndarray: Array with all negative values replaced by zero.
    """
    return np.where(array < 0, 0, array)


def extract_timestamp(filename_stem: str) -> str:
    """
    Extract timestamp from a filename stem.
    
    Args:
        filename_stem (str): The stem of the filename (without extension).
    
    Returns:
        str: Extracted timestamp or 'unknown' if not found.
    """
    match = re.search(r'(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})', filename_stem)
    return match.group(1) if match else "unknown"


def find_wavelength_index(wavelengths: np.ndarray, target_wavelength: float = TARGET_WAVELENGTH) -> int:
    """
    Find the index of the wavelength closest to the target wavelength.
    
    Args:
        wavelengths (np.ndarray): Array of wavelength values
        target_wavelength (float): Target wavelength to find
    
    Returns:
        int: Index of the closest wavelength
    """
    return int(np.argmin(np.abs(wavelengths - target_wavelength)))


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


def save_spectrum(wavelengths: np.ndarray, spectrum: np.ndarray, timestamp: str, 
                 filename: Optional[str] = None, reference: bool = False, 
                 t0: bool = False, absorbance: bool = False) -> Path:
    """
    Save spectrum data to users/data/UV_VIS_data folder with automatic type detection.
    
    Args:
        wavelengths (np.ndarray): Array of wavelength values.
        spectrum (np.ndarray): Array of intensity/absorbance values.
        timestamp (str): Timestamp string for filename.
        filename (str, optional): Optional filename. If None, generates timestamp-based name.
        reference (bool): True if this is a reference spectrum.
        t0 (bool): True if this is a t0 spectrum.
        absorbance (bool): True if this is an absorbance spectrum.
    
    Returns:
        Path: Path to the saved file.
    """
    spectra_folder = get_spectra_path()
    spectra_folder.mkdir(parents=True, exist_ok=True)
    if filename is None:
        if reference:
            filename = generate_filename(spectrum_type=PATTERN_REFERENCE, timestamp=timestamp)
        elif t0:
            filename = generate_filename(spectrum_type=PATTERN_T0, timestamp=timestamp)
        elif absorbance:
            filename = generate_filename(spectrum_type=PATTERN_ABSORBANCE, timestamp=timestamp)
        else:
            filename = generate_filename(spectrum_type="spectrum", timestamp=timestamp)
    file_path = spectra_folder / filename
    save_spectrum_file(file_path, wavelengths, spectrum, HEADER_INTENSITY, FMT_SPECTRUM)
    logger.info(f"Spectrum saved to {file_path}")
    return file_path


def check_absorbance_stability(data_folder: str = DATA_FOLDER, target_wavelength: float = TARGET_WAVELENGTH, 
                              num_measurements: int = DEFAULT_NUM_MEASUREMENTS, 
                              tolerance_percent: float = DEFAULT_TOLERANCE_PERCENT) -> bool:
    """
    Check if absorbance has stabilized by comparing the last N measurements.
    
    Args:
        data_folder (str): Path to folder containing absorbance files.
        target_wavelength (float): Wavelength to monitor (default: 520 nm).
        num_measurements (int): Number of recent measurements to compare (default: 5).
        tolerance_percent (float): Tolerance as percentage of t0 absorbance (default: 1.0%).
    
    Returns:
        bool: True if absorbance has stabilized, False otherwise.
    """
    spectra_path = get_spectra_path(data_folder)
    absorbance_files = find_files_by_pattern(spectra_path, PATTERN_ABSORBANCE)
    if len(absorbance_files) == 0:
        logger.warning("No absorbance files found for stability check!")
        return False
    
    # Find t0 absorbance file
    t0_files = [f for f in absorbance_files if PATTERN_T0 in str(f)]
    if len(t0_files) == 0:
        logger.warning("No t0 absorbance file found for stability check!")
        return False
    
    t0_data = load_spectrum_data(t0_files[0])
    if t0_data is None:
        logger.warning("Could not load t0 absorbance data for stability calculation")
        return False
    
    t0_wavelengths = t0_data[:, 0]
    t0_absorbances = t0_data[:, 1]
    wavelength_idx = find_wavelength_index(t0_wavelengths, target_wavelength)
    t0_absorbance_target = t0_absorbances[wavelength_idx]
    
    # Calculate absolute tolerance as percentage of t0 absorbance
    absolute_tolerance = (tolerance_percent / 100.0) * t0_absorbance_target
    
    # Get all absorbance files except reference and t0
    sample_files = [f for f in absorbance_files if PATTERN_REFERENCE not in str(f) and PATTERN_T0 not in str(f)]
    
    if len(sample_files) < num_measurements:
        return False  # Not enough measurements yet
    
    # Sort by timestamp and get the last N measurements
    sample_files.sort(key=lambda x: extract_timestamp(Path(x).stem))
    recent_files = sample_files[-num_measurements:]
    
    absorbance_values = []
    for file in recent_files:
        data = load_spectrum_data(file)
        if data is not None and validate_spectrum_data(data):
            wavelengths = data[:, 0]
            absorbances = data[:, 1]
            wavelength_idx = find_wavelength_index(wavelengths, target_wavelength)
            absorbance_values.append(absorbances[wavelength_idx])
    
    if len(absorbance_values) < num_measurements:
        return False  # Could not load all required measurements
    
    # Check if the difference between consecutive measurements is within tolerance
    for i in range(1, len(absorbance_values)):
        if abs(absorbance_values[i] - absorbance_values[i-1]) > absolute_tolerance:
            return False  # Significant change detected
    
    return True  # All measurements are within tolerance


def take_spectrum(reference: bool = False, t0: bool = False, calculate_conversion: bool = False, 
                 integration_time: float = DEFAULT_INTEGRATION_TIME) -> Tuple[Optional[np.ndarray], 
                                                                             Optional[np.ndarray], 
                                                                             Optional[str], 
                                                                             Optional[float], 
                                                                             bool]:
    """
    Take a spectrum using the CCS200 spectrometer and save it to the data folder.
    
    Args:
        reference (bool): If True, saves as reference spectrum.
        t0 (bool): If True, saves as t0 spectrum.
        calculate_conversion (bool): If True, runs full conversion pipeline after taking spectrum.
        integration_time (float): Integration time in seconds (default: 0.003).
    
    Returns:
        tuple: (spectrum, wavelengths, filename, conversion, reaction_complete)
            - spectrum: Array of intensity values
            - wavelengths: Array of wavelength values
            - filename: Name of saved file
            - conversion: Conversion value (if calculate_conversion=True and not reference/t0)
            - reaction_complete: True if absorbance has stabilized (if not reference/t0), False otherwise
    """
    spec = get_spectrometer()
    try:
        spectrum = spec.measure_spectrum(integration_time)
        wavelengths = spec.get_wavelength_data()
        timestamp = get_timestamp()
        
        # Check if we got valid data from spectrometer
        if spectrum is None or wavelengths is None:
            logger.error("Failed to get valid spectrum data from spectrometer")
            return None, None, None, None, False
        
        if reference:
            filename = generate_filename(PATTERN_REFERENCE, timestamp)
            save_spectrum(wavelengths, spectrum, timestamp, filename, reference=True)
            logger.info(f"Reference spectrum saved as {filename}")
            return spectrum, wavelengths, filename, None, False
        elif t0:
            filename = generate_filename(PATTERN_T0, timestamp)
            save_spectrum(wavelengths, spectrum, timestamp, filename, t0=True)
            logger.info(f"t0 spectrum saved as {filename}")
            return spectrum, wavelengths, filename, None, False
        else:
            filename = generate_filename("spectrum", timestamp)
            save_spectrum(wavelengths, spectrum, timestamp, filename)
            logger.info(f"Spectrum saved as {filename}")
            
            # Check if absorbance has stabilized (only for regular spectra, not reference/t0)
            reaction_complete = check_absorbance_stability()
            
            if calculate_conversion:
                # Run the full pipeline
                remove_negatives_from_spectra()
                calculate_absorbance()
                conversion_results = calculate_conversion_at_520nm()
                
                # Find the conversion for this specific spectrum
                conversion: Optional[float] = None
                if conversion_results and 'filenames' in conversion_results:
                    # Look for the most recent conversion (should be the one we just added)
                    filenames = conversion_results['filenames']
                    conversions = conversion_results['conversions']
                    if isinstance(filenames, list) and isinstance(conversions, list):
                        for i, filename_in_results in enumerate(filenames):
                            if isinstance(filename_in_results, str) and timestamp in filename_in_results:
                                conversion_value = conversions[i]
                                if isinstance(conversion_value, (int, float)):
                                    conversion = float(conversion_value)
                                break
                
                return spectrum, wavelengths, filename, conversion, reaction_complete
            else:
                return spectrum, wavelengths, filename, None, reaction_complete
                
    except Exception as e:
        logger.error(f"Error taking spectrum: {e}")
        return None, None, None, None, False
    finally:
        spec.close_instrument()


def remove_negatives_from_spectra(data_folder: str = DATA_FOLDER) -> List[Path]:
    """
    Preprocess all spectra by setting negative intensity values to zero and saving the result as new files
    with the '_neg_removed' suffix.

    Only processes original spectra: files that do NOT already contain 'neg_removed' in the filename.
    This includes reference, t0, and regular spectra.

    Args:
        data_folder (str): Path to the folder containing spectra files.

    Returns:
        list of Path: List of file paths to the new '_neg_removed' spectra. List may be empty if no files match.

    Notes:
        - The output files are saved in the same directory as the originals, with '_neg_removed' appended to the stem.
        - This function should be run before any absorbance or conversion analysis.
        - Uses find_files_by_patterns for robust file selection.
    """
    spectra_path = get_spectra_path(data_folder)
    files_to_process = find_files_by_patterns(
        spectra_path,
        include_patterns=None,
        exclude_patterns=[PATTERN_NEG_REMOVED]
    )
    
    results = []
    for file in files_to_process:
        data = load_spectrum_data(file)
        if not validate_spectrum_data(data):
            continue
        # Data is guaranteed to be valid at this point
        assert data is not None  # Help type checker
        wavelengths = data[:, 0]
        intensities = zero_negatives(data[:, 1])
        new_filename = file.with_name(file.stem + "_neg_removed.txt")
        save_spectrum_file(new_filename, wavelengths, intensities, HEADER_INTENSITY)
        logger.info(f"Saved negative-removed spectrum to {new_filename}")
        results.append(new_filename)
    return results


def calculate_absorbance(data_folder: str = DATA_FOLDER, reference_pattern: str = PATTERN_REFERENCE) -> List[np.ndarray]:
    """
    Calculate absorbance for all negative-removed sample spectra in the specified folder.

    For each sample spectrum (with '_neg_removed' in the filename and not containing 'reference', 't0', or 'absorbance'),
    calculate absorbance using the reference spectrum (matching reference_pattern and '_neg_removed').
    Both sample and reference intensities are preprocessed to set negative values to zero.
    Absorbance is calculated as -log10(sample_intensity / reference_intensity) at each wavelength.

    Args:
        data_folder (str): Path to folder containing spectra files.
        reference_pattern (str): Pattern to identify the reference spectrum (default: 'reference').

    Returns:
        list: List of absorbance data arrays, one per processed file. List may be empty if no files match.
    """
    spectra_path = get_spectra_path(data_folder)
    # Find reference spectrum (negative-removed)
    ref_files = find_files_by_patterns(spectra_path, include_patterns=["_neg_removed", reference_pattern], exclude_patterns=["absorbance"])
    if len(ref_files) == 0:
        logger.warning(f"No reference spectrum found with pattern '{reference_pattern}' and '_neg_removed'.")
        return []
    reference_data = load_spectrum_data(ref_files[0])
    if not validate_spectrum_data(reference_data):
        logger.warning("Reference spectrum is invalid.")
        return []
    # Reference data is guaranteed to be valid at this point
    assert reference_data is not None  # Help type checker
    ref_wavelengths = reference_data[:, 0]
    ref_intensities = zero_negatives(reference_data[:, 1])
    # Find all sample spectra (negative-removed, not reference, not absorbance, not t0)
    sample_files = find_files_by_patterns(
        spectra_path,
        include_patterns=["_neg_removed"],
        exclude_patterns=[reference_pattern, "absorbance"]
    )
    results = []
    for file in sample_files:
        data = load_spectrum_data(file)
        if not validate_spectrum_data(data):
            continue
        # Data is guaranteed to be valid at this point
        assert data is not None  # Help type checker
        wavelengths = data[:, 0]
        intensities = zero_negatives(data[:, 1])
        # Ensure wavelength alignment
        if not np.allclose(wavelengths, ref_wavelengths):
            logger.warning(f"Wavelength mismatch in {file}, skipping.")
            continue
        # Avoid divide by zero - protect both reference and sample intensities
        reference_intensities = np.where(ref_intensities == 0, MIN_REFERENCE_INTENSITY, ref_intensities)
        sample_intensities = np.where(intensities == 0, MIN_REFERENCE_INTENSITY, intensities)
        absorbance = -np.log10(sample_intensities / reference_intensities)
        base_name = Path(file).stem
        output_filename = file.with_name(base_name + "_absorbance.txt")
        save_spectrum_file(output_filename, wavelengths, absorbance, HEADER_ABSORBANCE)
        logger.info(f"Absorbance spectrum saved to {output_filename}")
        results.append(np.column_stack((wavelengths, absorbance)))
    return results


def calculate_conversion_at_520nm(data_folder: str = DATA_FOLDER) -> Dict[str, Union[List[str], List[float], float]]:
    """
    Calculate conversion at 520 nm from absorbance spectra.
    Conversion = 1 - (absorbance of spectrum) / (absorbance of t0)
    
    Args:
        data_folder (str): Path to folder containing absorbance files.
    
    Returns:
        dict: Dictionary containing:
            - filenames: List of filenames for each spectrum
            - absorbances: List of absorbance values at target wavelength
            - conversions: List of conversion values in percentage (1 - absorbance/t0_absorbance) * 100
            - t0_absorbance: Reference absorbance value from t0 spectrum
            - wavelength: Actual wavelength used (closest to 520 nm)
    """
    spectra_path = get_spectra_path(data_folder)
    absorbance_files = find_files_by_pattern(spectra_path, PATTERN_ABSORBANCE)
    if len(absorbance_files) == 0:
        logger.warning("No absorbance files found!")
        return {}
    
    # Find t0 absorbance file specifically
    t0_absorbance_files = [f for f in absorbance_files if PATTERN_T0 in str(f)]
    if len(t0_absorbance_files) == 0:
        logger.warning("No t0 absorbance file found!")
        return {}
    
    t0_file = t0_absorbance_files[0]
    t0_data = load_spectrum_data(t0_file)
    if t0_data is None or not validate_spectrum_data(t0_data):
        return {}
    
    t0_wavelengths = t0_data[:, 0]
    t0_absorbances = t0_data[:, 1]
    wavelength_idx = find_wavelength_index(t0_wavelengths, TARGET_WAVELENGTH)
    t0_absorbance_target = t0_absorbances[wavelength_idx]
    actual_wavelength = t0_wavelengths[wavelength_idx]
    logger.info(f"Using absorbance at {actual_wavelength:.1f} nm (closest to {TARGET_WAVELENGTH} nm)")
    logger.info(f"t0 absorbance: {t0_absorbance_target:.6f}")
    
    # Process all absorbance files except reference
    files_to_process = [f for f in absorbance_files if PATTERN_REFERENCE not in str(f)]
    
    # Check for existing conversion values to avoid reprocessing
    existing_conversion_file = spectra_path / "conversion_values.txt"
    already_processed = set()
    if existing_conversion_file.exists():
        try:
            with open(existing_conversion_file, "r") as f:
                lines = f.readlines()
                for line in lines[1:]:  # Skip header
                    if line.strip():
                        filename = line.split('\t')[0]
                        already_processed.add(filename)
        except Exception as e:
            logger.warning(f"Could not read existing conversion file: {e}")
    
    conversion_data = []
    
    for file in files_to_process:
        filename = Path(file).name
        if filename in already_processed:
            logger.info(f"Skipping {filename} - already processed")
            continue
        
        spectrum_data = load_spectrum_data(file)
        if spectrum_data is not None and validate_spectrum_data(spectrum_data):
            wavelengths = spectrum_data[:, 0]
            absorbances = spectrum_data[:, 1]
            if not np.array_equal(wavelengths, t0_wavelengths):
                logger.warning(f"Warning: Wavelength mismatch in {file}")
                continue
            absorbance_target = absorbances[wavelength_idx]
            
            # Calculate conversion: t0 = 0%, others = (1 - absorbance/t0_absorbance) * 100
            if PATTERN_T0 in str(file):
                conversion = 0.0  # t0 spectrum is 0% conversion
            elif t0_absorbance_target > 0:
                conversion = (1 - (absorbance_target / t0_absorbance_target)) * 100
            else:
                logger.warning(f"Warning: t0 absorbance at {actual_wavelength:.1f} nm is zero or negative")
                conversion = 0.0
            
            conversion_data.append({
                'filename': filename,
                'absorbance': absorbance_target,
                'conversion': conversion,
                'file': file
            })
    
    # Sort by timestamp extracted from filename
    conversion_data.sort(key=lambda x: extract_timestamp(Path(x['file']).stem))
    if conversion_data:
        file_path = spectra_path / "conversion_values.txt"
        # Read existing data if file exists
        existing_data = []
        if file_path.exists():
            try:
                with open(file_path, "r") as f:
                    lines = f.readlines()
                    if lines:  # Keep header from existing file
                        header = lines[0]
                        for line in lines[1:]:
                            if line.strip():
                                parts = line.strip().split('\t')
                                if len(parts) >= 3:
                                    existing_data.append({
                                        'filename': parts[0],
                                        'absorbance': float(parts[1]),
                                        'conversion': float(parts[2]),
                                        'timestamp': extract_timestamp(parts[0])
                                    })
            except Exception as e:
                logger.warning(f"Could not read existing conversion file: {e}")
                header = HEADER_CONVERSION
        else:
            header = HEADER_CONVERSION
        
        # Combine existing and new data
        all_data = existing_data + conversion_data
        
        # Sort all data by timestamp
        def get_timestamp_for_sorting(item):
            if 'timestamp' in item:
                return item['timestamp']  # Existing data
            else:
                return extract_timestamp(Path(item['file']).stem)  # New data
        
        all_data.sort(key=get_timestamp_for_sorting)
        
        # Write all data back to file
        with open(file_path, "w") as f:
            f.write(header)
            for row in all_data:
                if 'file' in row:  # New data
                    f.write(f"{row['filename']}\t{row['absorbance']:.6f}\t{row['conversion']:.2f}\n")
                else:  # Existing data
                    f.write(f"{row['filename']}\t{row['absorbance']:.6f}\t{row['conversion']:.2f}\n")
        logger.info(f"Conversion data saved to {file_path}")
    
    return {
        'filenames': [d['filename'] for d in conversion_data],
        'absorbances': [d['absorbance'] for d in conversion_data],
        'conversions': [d['conversion'] for d in conversion_data],
        't0_absorbance': t0_absorbance_target,
        'wavelength': actual_wavelength
    }


