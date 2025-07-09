"""
UV-VIS Spectroscopy Utilities Module

This module provides comprehensive tools for UV-VIS spectroscopy data acquisition, processing,
and analysis in automated polymerization workflows. It includes functions for spectrum
acquisition, baseline correction, absorbance calculation, and conversion analysis.

Key Features:
    - Automated spectrum acquisition using CCS200 spectrometer
    - Baseline correction for all spectra in a folder
    - Absorbance calculation using baseline as reference
    - Conversion analysis at specific wavelengths (e.g., 520 nm)
    - Batch processing of multiple spectrum files
    - Automatic file organization and naming conventions
    - Robust error handling and validation

Spectrum Types Supported:
    - Baseline spectra: Reference spectra for background correction
    - t0 spectra: Initial time point spectra for conversion calculations
    - Regular spectra: Sample spectra for analysis
    - Corrected spectra: Baseline-subtracted spectra
    - Absorbance spectra: Calculated absorbance values

File Naming Conventions:
    - Baseline: UV_VIS_baseline_spectrum_YYYY-MM-DD_HH-MM-SS.txt
    - t0: UV_VIS_t0_spectrum_YYYY-MM-DD_HH-MM-SS.txt
    - Regular: UV_VIS_spectrum_YYYY-MM-DD_HH-MM-SS.txt
    - Corrected: {original_name}_corrected.txt
    - Absorbance: {original_name}_absorbance.txt
    - Conversion: conversion_at_520nm_YYYY-MM-DD_HH-MM-SS.txt

Data Format:
    All spectrum files are saved as tab-separated text files with header:
    "Wavelength (nm)\tIntensity (a.u.)" or "Wavelength (nm)\tAbsorbance (a.u.)"

Dependencies:
    - numpy: For numerical operations and array handling
    - matplotlib: For spectrum plotting
    - matterlab_spectrometers: For spectrometer communication
    - pathlib: For cross-platform path handling
    - glob: For file pattern matching

Hardware Requirements:
    - CCS200 spectrometer (USB connection)
    - Device ID: M00479664
    - Default integration time: 3 ms

Usage Example:
    # Take a baseline spectrum
    spectrum, wavelengths, filename = take_spectrum(baseline=True)
    
    # Take a t0 spectrum
    spectrum, wavelengths, filename = take_spectrum(t0=True)
    
    # Take regular sample spectra
    spectrum, wavelengths, filename = take_spectrum()
    
    # Process all spectra (baseline correction)
    corrected_data = subtract_baseline_from_spectra()
    
    # Calculate absorbance for all corrected spectra
    absorbance_data = calculate_absorbance()
    
    # Calculate conversion at 520 nm
    conversion_data = calculate_conversion_at_520nm()
    
    # Plot a spectrum
    plot_spectrum(wavelengths, spectrum, "Sample Spectrum")

Author: Michael Ringleb (help from cursor.ai)
Date: [08.07.2025]
Version: 0.1
"""

# Controls the uv_vis measurements 
import sys
import os
import time
import serial
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from datetime import datetime
import glob
import re
from matterlab_spectrometers.ccs_spectrometer import CCSSpectrometer

# Definition of the spectrometer
spec = CCSSpectrometer(
    usb_port="USB",
    device_model="CCS200",
    device_id="M00479664"
)

# Definition of integration time (default is 3 ms)
INTEGRATION_TIME = 0.003

# Constants
TARGET_WAVELENGTH = 520  # nm
DATA_FOLDER = "users/data/UV_VIS_data"

def get_project_path():
    """Get the project root path."""
    return Path(__file__).resolve().parents[3]

def get_spectra_path(data_folder=DATA_FOLDER):
    """Get the spectra data path."""
    return get_project_path() / data_folder

def find_files_by_pattern(spectra_path, pattern):
    """Find files containing a specific pattern using numpy operations."""
    files = np.array(glob.glob(str(spectra_path / "*.txt")))
    if len(files) == 0:
        return np.array([])
    
    mask = np.char.find(files.astype(str), pattern) >= 0
    return files[mask]

def load_spectrum_data(file_path):
    """Load spectrum data from file."""
    try:
        return np.loadtxt(file_path, skiprows=1)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None

def extract_timestamp(filename):
    """Extract timestamp from filename using regex."""
    match = re.search(r'(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})', filename)
    return match.group(1) if match else "unknown"

def take_spectrum(baseline=False, t0=False, calculate_conversion=False):
    """
    Take a spectrum using the spectrometer and save it with appropriate naming.
    
    Args:
        baseline (bool): True if this is a baseline spectrum
        t0 (bool): True if this is a t0 spectrum
        calculate_conversion (bool): True to calculate conversion from latest spectrum
    
    Returns:
        tuple: (spectrum_data, wavelengths, filename, conversion_value)
        conversion_value is None if calculate_conversion=False or not applicable
    """
    spectrum = spec.measure_spectrum(INTEGRATION_TIME)
    wavelengths = spec.get_wavelength_data()
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"UV_VIS_spectrum_{timestamp}.txt"
    save_spectrum(wavelengths, spectrum, timestamp, filename, baseline, t0)
    
    conversion_value = None
    if calculate_conversion and not baseline and not t0:
        # Process the spectrum through the pipeline to get conversion
        subtract_baseline_from_spectra()
        calculate_absorbance()
        conversion_data = calculate_conversion_at_520nm()
        if conversion_data and 'conversions' in conversion_data:
            conversion_value = conversion_data['conversions'][-1] if conversion_data['conversions'] else None
    
    return spectrum, wavelengths, filename, conversion_value

def save_spectrum(wavelengths, spectrum, timestamp, filename=None, baseline=False, t0=False, absorbance=False):
    """
    Save spectrum data to users/data/UV_VIS_data folder with automatic type detection.
    
    Args:
        wavelengths: Array of wavelength values
        spectrum: Array of intensity/absorbance values
        timestamp: Timestamp string for filename
        filename (str): Optional filename. If None, generates timestamp-based name
        baseline (bool): True if this is a baseline spectrum
        t0 (bool): True if this is a t0 spectrum
        absorbance (bool): True if this is an absorbance spectrum
    """
    spectra_folder = get_spectra_path()
    spectra_folder.mkdir(parents=True, exist_ok=True)
    
    # Determine filename based on spectrum type
    if baseline:
        filename = f"UV_VIS_baseline_spectrum_{timestamp}.txt"
    elif t0:
        filename = f"UV_VIS_t0_spectrum_{timestamp}.txt"
    elif absorbance:
        filename = f"UV_VIS_absorbance_spectrum_{timestamp}.txt"
    elif filename is None:
        filename = f"UV_VIS_spectrum_{timestamp}.txt"
   
    file_path = spectra_folder / filename
    data = np.column_stack((wavelengths, spectrum))
    np.savetxt(file_path, data, header="Wavelength (nm)\tIntensity (a.u.)", fmt="%.4f\t%.6f")
    
    print(f"Spectrum saved to {file_path}")
    return file_path

def process_spectra_files(operation_func, data_folder=DATA_FOLDER, **kwargs):
    """
    Generic function to process spectrum files with common logic.
    
    Args:
        operation_func: Function to apply to each spectrum
        data_folder: Path to folder containing spectra files
        **kwargs: Additional arguments for operation_func
    
    Returns:
        dict: Results from processing
    """
    spectra_path = get_spectra_path(data_folder)
    spectrum_files = find_files_by_pattern(spectra_path, "")
    
    if len(spectrum_files) == 0:
        print("No spectrum files found!")
        return {}
    
    # Find baseline file
    baseline_files = find_files_by_pattern(spectra_path, 'baseline')
    if len(baseline_files) == 0:
        print("No baseline file found!")
        return {}
    
    baseline_file = baseline_files[0]
    baseline_data = load_spectrum_data(baseline_file)
    if baseline_data is None:
        return {}
    
    baseline_wavelengths = baseline_data[:, 0]
    baseline_intensities = baseline_data[:, 1]
    
    # Create masks for filtering files
    baseline_mask = np.char.find(spectrum_files.astype(str), 'baseline') >= 0
    corrected_mask = np.char.find(spectrum_files.astype(str), 'corrected') >= 0
    
    # Determine which files to process based on operation
    if 'absorbance' in operation_func.__name__:
        process_mask = corrected_mask & ~baseline_mask
    else:
        process_mask = ~(baseline_mask | corrected_mask)
    
    files_to_process = spectrum_files[process_mask]
    results = {}
    
    for file in files_to_process:
        spectrum_data = load_spectrum_data(file)
        if spectrum_data is None:
            continue
            
        wavelengths = spectrum_data[:, 0]
        intensities = spectrum_data[:, 1]
        
        if not np.array_equal(wavelengths, baseline_wavelengths):
            print(f"Warning: Wavelength mismatch in {file}")
            continue
        
        # Apply the specific operation
        result = operation_func(wavelengths, intensities, baseline_intensities, file, **kwargs)
        if result is not None:
            results[file] = result
    
    return results

def subtract_baseline_operation(wavelengths, intensities, baseline_intensities, file, **kwargs):
    """Operation function for baseline subtraction."""
    corrected_intensities = intensities - baseline_intensities
    base_name = Path(file).stem
    output_filename = f"{base_name}_corrected.txt"
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    save_spectrum(wavelengths, corrected_intensities, timestamp, output_filename)
    return np.column_stack((wavelengths, corrected_intensities))

def calculate_absorbance_operation(wavelengths, intensities, baseline_intensities, file, **kwargs):
    """Operation function for absorbance calculation."""
    reference_intensities = np.where(baseline_intensities <= 0, 1e-10, baseline_intensities)
    absorbance = -np.log10(intensities / reference_intensities)
    
    base_name = Path(file).stem
    if base_name.endswith("_corrected"):
        base_name = base_name[:-10]
    output_filename = f"{base_name}_absorbance.txt"
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    save_spectrum(wavelengths, absorbance, timestamp, output_filename, absorbance=True)
    return np.column_stack((wavelengths, absorbance))

def subtract_baseline_from_spectra(data_folder=DATA_FOLDER):
    """Subtract baseline from all spectra in folder."""
    return process_spectra_files(subtract_baseline_operation, data_folder)

def calculate_absorbance(data_folder=DATA_FOLDER):
    """Calculate absorbance for all corrected spectra."""
    return process_spectra_files(calculate_absorbance_operation, data_folder)

def calculate_conversion_at_520nm(data_folder=DATA_FOLDER):
    """
    Calculate conversion at 520 nm from absorbance spectra.
    Conversion = 1 - (absorbance of spectrum) / (absorbance of t0)
    
    Args:
        data_folder (str): Path to folder containing absorbance files
    
    Returns:
        dict: Dictionary containing:
            - timestamps: List of timestamps for each spectrum
            - absorbances: List of absorbance values at target wavelength
            - conversions: List of conversion values (1 - absorbance/t0_absorbance)
            - t0_absorbance: Reference absorbance value from t0 spectrum
            - wavelength: Actual wavelength used (closest to 520 nm)
    """
    spectra_path = get_spectra_path(data_folder)
    absorbance_files = find_files_by_pattern(spectra_path, 'absorbance')
    
    if len(absorbance_files) == 0:
        print("No absorbance files found!")
        return {}
    
    # Find t0 absorbance file
    t0_files = find_files_by_pattern(spectra_path, 't0')
    if len(t0_files) == 0:
        print("No t0 absorbance file found!")
        return {}
    
    t0_file = t0_files[0]
    t0_data = load_spectrum_data(t0_file)
    if t0_data is None:
        return {}
    
    t0_wavelengths = t0_data[:, 0]
    t0_absorbances = t0_data[:, 1]
    
    # Find closest wavelength to target
    wavelength_idx = np.argmin(np.abs(t0_wavelengths - TARGET_WAVELENGTH))
    t0_absorbance_target = t0_absorbances[wavelength_idx]
    actual_wavelength = t0_wavelengths[wavelength_idx]
    
    print(f"Using absorbance at {actual_wavelength:.1f} nm (closest to {TARGET_WAVELENGTH} nm)")
    print(f"t0 absorbance: {t0_absorbance_target:.6f}")
    
    # Process all absorbance files (excluding t0)
    t0_mask = np.char.find(absorbance_files.astype(str), 't0') >= 0
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
            print(f"Warning: Wavelength mismatch in {file}")
            continue
        
        absorbance_target = absorbances[wavelength_idx]
        
        # Calculate conversion: 1 - (absorbance / t0_absorbance)
        if t0_absorbance_target > 0:
            conversion = 1 - (absorbance_target / t0_absorbance_target)
        else:
            print(f"Warning: t0 absorbance at {actual_wavelength:.1f} nm is zero or negative")
            conversion = 0
        
        timestamp = extract_timestamp(Path(file).stem)
        
        conversion_data.append({
            'timestamp': timestamp,
            'absorbance': absorbance_target,
            'conversion': conversion,
            'file': file
        })
    
    # Sort by timestamp
    conversion_data.sort(key=lambda x: x['timestamp'])
    
    # Save results
    if conversion_data:
        timestamp_save = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        conversion_filename = f"conversion_at_{actual_wavelength:.0f}nm_{timestamp_save}.txt"
        file_path = spectra_path / conversion_filename
        
        data_array = np.array([[d['timestamp'], d['absorbance'], d['conversion']] 
                              for d in conversion_data])
        np.savetxt(file_path, data_array, 
                   header="Timestamp\tAbsorbance\tConversion", 
                   fmt="%s\t%.6f\t%.6f")
        
        print(f"Conversion data saved to {file_path}")
    
    return {
        'timestamps': [d['timestamp'] for d in conversion_data],
        'absorbances': [d['absorbance'] for d in conversion_data],
        'conversions': [d['conversion'] for d in conversion_data],
        't0_absorbance': t0_absorbance_target,
        'wavelength': actual_wavelength
    }

def plot_spectrum(wavelengths, spectrum, title):
    """
    Plot spectrum with proper formatting.
    
    Args:
        wavelengths: Array of wavelength values
        spectrum: Array of intensity/absorbance values
        title: Title for the plot
    """
    plt.figure()
    plt.plot(wavelengths, spectrum)
    plt.xlabel("Wavelength (nm)")
    plt.ylabel("Intensity (a.u.)")
    plt.title(title)
    plt.grid(True)
    plt.show(block=False)
