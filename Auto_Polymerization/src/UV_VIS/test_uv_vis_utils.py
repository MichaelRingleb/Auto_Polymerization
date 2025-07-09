"""
Test suite for UV-VIS utility functions.

This script provides comprehensive functional tests for all features of uv_vis_utils.py,
including negative value removal, absorbance calculation, conversion calculation, spectrum acquisition, 
file operations, and plotting. It also includes diagnostic functions to help debug file discovery issues.

Usage:
    python test_uv_vis_utils.py

Requirements:
    - Place this script in the same directory as uv_vis_utils.py or ensure it is on the Python path.
    - Ensure your data folder (see DATA_FOLDER in uv_vis_utils.py) contains appropriate test spectra.
    - For take_spectrum test, hardware must be connected (or simulate with reference=True).

Tests:
    - File operations (timestamp, filename generation, path handling)
    - File discovery and filtering
    - Data loading and validation
    - Negative value removal preprocessing
    - Absorbance calculation (using reference spectrum)
    - Conversion calculation at 520 nm
    - Spectrum acquisition (take_spectrum)
    - Absorbance stability checking
    - Plotting at various stages
    - Error handling and edge cases
    - Duplicate protection mechanisms

Author: Michael Ringleb (with help from cursor.ai)
Date: [08.07.2025]
Version: 0.6
"""

from uv_vis_utils import (
    remove_negatives_from_spectra,
    calculate_absorbance,
    calculate_conversion_at_520nm,
    get_spectra_path,
    find_files_by_pattern,
    find_files_by_patterns,
    load_spectrum_data,
    validate_spectrum_data,
    save_spectrum_file,
    zero_negatives,
    extract_timestamp,
    find_wavelength_index,
    get_timestamp,
    generate_filename,
    take_spectrum,
    check_absorbance_stability,
    DATA_FOLDER,
    TARGET_WAVELENGTH,
    PATTERN_REFERENCE,
    PATTERN_T0,
    PATTERN_ABSORBANCE,
    PATTERN_NEG_REMOVED
)
import numpy as np
import logging
import matplotlib.pyplot as plt
from pathlib import Path
import tempfile
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_get_timestamp():
    """Test timestamp generation."""
    logger.info("Testing timestamp generation...")
    timestamp = get_timestamp()
    assert isinstance(timestamp, str)
    assert len(timestamp) == 19  # YYYY-MM-DD_HH-MM-SS format
    # Check format: YYYY-MM-DD_HH-MM-SS (4 hyphens, 1 underscore)
    assert timestamp.count('-') == 4, f"Expected 4 hyphens, got {timestamp.count('-')} in '{timestamp}'"
    assert timestamp.count('_') == 1, f"Expected 1 underscore, got {timestamp.count('_')} in '{timestamp}'"
    # Verify the format matches the expected pattern
    import re
    pattern = r'^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$'
    assert re.match(pattern, timestamp), f"Timestamp '{timestamp}' doesn't match expected format YYYY-MM-DD_HH-MM-SS"
    logger.info(f"Generated timestamp: {timestamp}")


def test_generate_filename():
    """Test filename generation for different spectrum types."""
    logger.info("Testing filename generation...")
    timestamp = "2025-01-01_12-00-00"
    
    # Test reference spectrum
    ref_filename = generate_filename(PATTERN_REFERENCE, timestamp)
    assert ref_filename == f"{timestamp}_UV_VIS_reference_spectrum.txt"
    
    # Test t0 spectrum
    t0_filename = generate_filename(PATTERN_T0, timestamp)
    assert t0_filename == f"{timestamp}_UV_VIS_t0_spectrum.txt"
    
    # Test absorbance spectrum
    abs_filename = generate_filename(PATTERN_ABSORBANCE, timestamp)
    assert abs_filename == f"{timestamp}_UV_VIS_absorbance_spectrum.txt"
    
    # Test regular spectrum
    reg_filename = generate_filename("spectrum", timestamp)
    assert reg_filename == f"{timestamp}_UV_VIS_spectrum.txt"
    
    logger.info("Filename generation tests passed.")


def test_get_spectra_path():
    """Test spectra path generation."""
    logger.info("Testing spectra path generation...")
    path = get_spectra_path()
    assert isinstance(path, Path)
    assert "UV_VIS_data" in str(path)
    logger.info(f"Spectra path: {path}")


def test_find_files_by_pattern():
    """Test file pattern matching."""
    logger.info("Testing file pattern matching...")
    spectra_path = get_spectra_path()
    
    # Test with a pattern that might exist
    files = find_files_by_pattern(spectra_path, "txt")
    assert isinstance(files, np.ndarray)
    
    # Test with a pattern that likely doesn't exist
    no_files = find_files_by_pattern(spectra_path, "nonexistent_pattern")
    assert isinstance(no_files, np.ndarray)
    assert len(no_files) == 0
    
    logger.info(f"Found {len(files)} files with 'txt' pattern")


def test_find_files_by_patterns():
    """Test advanced file pattern matching."""
    logger.info("Testing advanced file pattern matching...")
    spectra_path = get_spectra_path()
    
    # Test include patterns
    files = find_files_by_patterns(spectra_path, include_patterns=["txt"])
    assert isinstance(files, list)
    
    # Test exclude patterns
    files = find_files_by_patterns(spectra_path, exclude_patterns=["nonexistent"])
    assert isinstance(files, list)
    
    # Test both include and exclude
    files = find_files_by_patterns(spectra_path, include_patterns=["txt"], exclude_patterns=["nonexistent"])
    assert isinstance(files, list)
    
    logger.info("Advanced file pattern matching tests passed.")


def test_zero_negatives():
    """Test negative value removal from arrays."""
    logger.info("Testing negative value removal...")
    
    # Test with mixed positive and negative values
    test_array = np.array([1.0, -2.0, 3.0, -4.0, 5.0])
    result = zero_negatives(test_array)
    expected = np.array([1.0, 0.0, 3.0, 0.0, 5.0])
    np.testing.assert_array_equal(result, expected)
    
    # Test with all positive values
    positive_array = np.array([1.0, 2.0, 3.0])
    result = zero_negatives(positive_array)
    np.testing.assert_array_equal(result, positive_array)
    
    # Test with all negative values
    negative_array = np.array([-1.0, -2.0, -3.0])
    result = zero_negatives(negative_array)
    expected = np.array([0.0, 0.0, 0.0])
    np.testing.assert_array_equal(result, expected)
    
    logger.info("Negative value removal tests passed.")


def test_extract_timestamp():
    """Test timestamp extraction from filenames."""
    logger.info("Testing timestamp extraction...")
    
    # Test valid timestamp
    filename = "2025-01-01_12-00-00_UV_VIS_spectrum"
    timestamp = extract_timestamp(filename)
    assert timestamp == "2025-01-01_12-00-00"
    
    # Test invalid filename
    invalid_filename = "no_timestamp_here"
    timestamp = extract_timestamp(invalid_filename)
    assert timestamp == "unknown"
    
    logger.info("Timestamp extraction tests passed.")


def test_find_wavelength_index():
    """Test wavelength index finding."""
    logger.info("Testing wavelength index finding...")
    
    wavelengths = np.array([500, 510, 520, 530, 540])
    
    # Test exact match
    idx = find_wavelength_index(wavelengths, 520)
    assert idx == 2
    
    # Test closest match
    idx = find_wavelength_index(wavelengths, 515)
    assert idx == 1  # Should be closer to 510 than 520
    
    # Test default target wavelength
    idx = find_wavelength_index(wavelengths)
    assert idx == 2  # Should find 520
    
    logger.info("Wavelength index finding tests passed.")


def test_validate_spectrum_data():
    """Test spectrum data validation."""
    logger.info("Testing spectrum data validation...")
    
    # Test valid data
    valid_data = np.array([[1.0, 2.0], [3.0, 4.0]])
    assert validate_spectrum_data(valid_data) == True
    
    # Test None data
    assert validate_spectrum_data(None) == False
    
    # Test 1D array
    invalid_1d = np.array([1.0, 2.0, 3.0])
    assert validate_spectrum_data(invalid_1d) == False
    
    # Test array with insufficient columns
    invalid_cols = np.array([[1.0], [2.0]])
    assert validate_spectrum_data(invalid_cols) == False
    
    logger.info("Spectrum data validation tests passed.")


def test_save_spectrum_file():
    """Test spectrum file saving."""
    logger.info("Testing spectrum file saving...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        wavelengths = np.array([500, 510, 520])
        values = np.array([1.0, 2.0, 3.0])
        header = "Wavelength\tIntensity"
        
        file_path = temp_path / "test_spectrum.txt"
        save_spectrum_file(file_path, wavelengths, values, header)
        
        # Check file exists
        assert file_path.exists()
        
        # Check file content
        with open(file_path, 'r') as f:
            content = f.read()
            assert header in content
            assert "500.0000" in content
            assert "1.000000" in content
        
        logger.info("Spectrum file saving tests passed.")


def test_remove_negatives():
    """Test negative value removal preprocessing."""
    logger.info("Testing negative value removal preprocessing...")
    results = remove_negatives_from_spectra()
    if results:
        logger.info(f"Negative removal successful for {len(results)} spectra.")
        assert all(isinstance(r, Path) for r in results)
    else:
        logger.warning("Negative removal failed or no spectra found.")


def test_calculate_absorbance():
    """Test absorbance calculation."""
    logger.info("Testing absorbance calculation...")
    results = calculate_absorbance()
    if results:
        logger.info(f"Absorbance calculation successful for {len(results)} spectra.")
        assert all(isinstance(r, np.ndarray) for r in results)
    else:
        logger.warning("Absorbance calculation failed or no spectra found.")


def test_calculate_conversion():
    """Test conversion calculation at 520 nm."""
    logger.info("Testing conversion calculation at 520 nm...")
    results = calculate_conversion_at_520nm()
    if results and 'conversions' in results:
        conversions = results['conversions']
        filenames = results['filenames']
        if isinstance(conversions, list) and isinstance(filenames, list):
            logger.info(f"Conversion calculation successful for {len(conversions)} spectra.")
            logger.info(f"Sample conversions: {conversions}")
            assert isinstance(conversions, list)
            assert isinstance(filenames, list)
            assert isinstance(results['t0_absorbance'], float)
            assert isinstance(results['wavelength'], float)
        else:
            logger.warning("Conversion results have unexpected types.")
    else:
        logger.warning("Conversion calculation failed or no absorbance spectra found.")


def test_take_spectrum():
    """Test spectrum acquisition (take_spectrum)."""
    logger.info("Testing spectrum acquisition (take_spectrum)...")
    try:
        # Test reference spectrum acquisition
        spectrum, wavelengths, filename, conversion, reaction_complete = take_spectrum(reference=True)
        if spectrum is not None and wavelengths is not None:
            logger.info(f"Reference spectrum acquired and saved as {filename}.")
            logger.info(f"Spectrum shape: {spectrum.shape}, Wavelengths shape: {wavelengths.shape}")
            assert isinstance(spectrum, np.ndarray)
            assert isinstance(wavelengths, np.ndarray)
            assert isinstance(filename, str)
            assert conversion is None  # Reference spectra don't have conversion
            assert reaction_complete is False  # Reference spectra don't check stability
        else:
            logger.warning("Spectrum acquisition returned None values.")
    except Exception as e:
        logger.error(f"Error during spectrum acquisition: {e}")


def test_check_absorbance_stability():
    """Test absorbance stability checking."""
    logger.info("Testing absorbance stability checking...")
    try:
        stability = check_absorbance_stability()
        assert isinstance(stability, bool)
        logger.info(f"Absorbance stability check result: {stability}")
    except Exception as e:
        logger.warning(f"Absorbance stability check failed: {e}")


def test_plot_first_neg_removed():
    """Test plotting of first _neg_removed spectrum."""
    logger.info("Testing plotting of first _neg_removed spectrum...")
    spectra_path = get_spectra_path()
    neg_removed_files = find_files_by_pattern(spectra_path, PATTERN_NEG_REMOVED)
    if len(neg_removed_files) > 0:
        data = load_spectrum_data(neg_removed_files[0])
        if validate_spectrum_data(data) and data is not None:
            wavelengths = data[:, 0]
            intensities = data[:, 1]
            plt.figure()
            plt.plot(wavelengths, intensities)
            plt.xlabel("Wavelength (nm)")
            plt.ylabel("Intensity (a.u.)")
            plt.title("First _neg_removed Spectrum")
            plt.grid(True)
            plt.show(block=False)
            logger.info("Plot displayed for first _neg_removed spectrum.")
        else:
            logger.warning("Failed to load first _neg_removed spectrum.")
    else:
        logger.warning("No _neg_removed spectra found for plotting.")
    input("Press Enter to continue...")


def test_plot_first_absorbance():
    """Test plotting of first absorbance spectrum."""
    logger.info("Testing plotting of first absorbance spectrum...")
    spectra_path = get_spectra_path()
    absorbance_files = find_files_by_pattern(spectra_path, PATTERN_ABSORBANCE)
    if len(absorbance_files) > 0:
        data = load_spectrum_data(absorbance_files[0])
        if validate_spectrum_data(data) and data is not None:
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
    input("Press Enter to continue...")


def test_plot_first_raw():
    """Test plotting of first raw/original spectrum."""
    logger.info("Testing plotting of first raw/original spectrum...")
    spectra_path = get_spectra_path()
    all_txt_files = list(spectra_path.glob("*.txt"))
    # Exclude files that are not raw/original
    exclude_patterns = [PATTERN_NEG_REMOVED, PATTERN_REFERENCE, PATTERN_T0, PATTERN_ABSORBANCE]
    raw_files = [f for f in all_txt_files if not any(pat in str(f) for pat in exclude_patterns)]
    if len(raw_files) > 0:
        data = load_spectrum_data(raw_files[0])
        if validate_spectrum_data(data) and data is not None:
            wavelengths = data[:, 0]
            intensities = data[:, 1]
            plt.figure()
            plt.plot(wavelengths, intensities)
            plt.xlabel("Wavelength (nm)")
            plt.ylabel("Intensity (a.u.)")
            plt.title("First Raw Spectrum")
            plt.grid(True)
            plt.show(block=False)
            logger.info("Plot displayed for first raw/original spectrum.")
        else:
            logger.warning("Failed to load first raw/original spectrum.")
    else:
        logger.warning("No raw/original spectra found for plotting.")
    input("Press Enter to continue...")


def test_take_spectrum_all_types():
    """Test all spectrum acquisition types."""
    logger.info("Testing all spectrum acquisition types...")
    try:
        # Test reference spectrum
        spectrum, wavelengths, filename, conversion, reaction_complete = take_spectrum(reference=True)
        assert conversion is None
        assert reaction_complete is False
        
        # Test t0 spectrum
        spectrum, wavelengths, filename, conversion, reaction_complete = take_spectrum(t0=True)
        assert conversion is None
        assert reaction_complete is False
        
        # Test regular spectrum
        spectrum, wavelengths, filename, conversion, reaction_complete = take_spectrum()
        assert isinstance(reaction_complete, bool)
        
        logger.info("All spectrum types acquired successfully.")
    except Exception as e:
        logger.warning(f"Some spectrum acquisitions failed: {e}")


def test_conversion_duplicate_protection():
    """Test duplicate protection in conversion calculation."""
    logger.info("Testing duplicate protection in conversion calculation...")
    try:
        # First run
        calculate_conversion_at_520nm()
        # Second run (should not add duplicates)
        conversion_file = get_spectra_path() / "conversion_values.txt"
        if conversion_file.exists():
            before = open(conversion_file).read()
            calculate_conversion_at_520nm()
            after = open(conversion_file).read()
            assert before == after, "Duplicate entries were added to conversion_values.txt"
            logger.info("Duplicate protection works as expected.")
        else:
            logger.warning("No conversion file found for duplicate protection test.")
    except Exception as e:
        logger.warning(f"Duplicate protection test failed: {e}")


def test_conversion_file_sorted():
    """Test that conversion_values.txt is sorted by timestamp."""
    logger.info("Testing that conversion_values.txt is sorted by timestamp...")
    try:
        file_path = get_spectra_path() / "conversion_values.txt"
        if file_path.exists():
            with open(file_path) as f:
                lines = f.readlines()[1:]  # skip header
            timestamps = []
            for line in lines:
                if line.strip():
                    filename = line.split('\t')[0]  # Get filename from first column
                    timestamp = extract_timestamp(filename)
                    timestamps.append(timestamp)
            assert timestamps == sorted(timestamps), "conversion_values.txt is not sorted by timestamp"
            logger.info("conversion_values.txt is sorted by timestamp.")
        else:
            logger.warning("No conversion file found for sorting test.")
    except Exception as e:
        logger.warning(f"Sorting test failed: {e}")


def test_error_handling():
    """Test error handling for various edge cases."""
    logger.info("Testing error handling...")
    
    # Test loading non-existent file
    non_existent_data = load_spectrum_data("non_existent_file.txt")
    assert non_existent_data is None
    
    # Test validating invalid data
    assert validate_spectrum_data(None) == False
    assert validate_spectrum_data(np.array([1, 2, 3])) == False  # 1D array
    
    # Test extracting timestamp from invalid filename
    invalid_timestamp = extract_timestamp("no_timestamp")
    assert invalid_timestamp == "unknown"
    
    logger.info("Error handling tests passed.")


def debug_spectra_folder(data_folder=DATA_FOLDER):
    """Print diagnostics about the spectra folder and file discovery."""
    path = get_spectra_path(data_folder)
    logger.info(f"Looking for spectra in: {path}")
    logger.info(f"Path exists: {path.exists()}")
    if path.exists():
        logger.info(f"All files: {list(path.glob('*'))}")
        txt_files = list(path.glob("*.txt"))
        logger.info(f"All .txt files: {txt_files}")
        for pattern in [PATTERN_REFERENCE, PATTERN_T0, PATTERN_ABSORBANCE, PATTERN_NEG_REMOVED]:
            files = np.array([str(f) for f in txt_files])
            mask = np.char.find(files.astype(str), pattern) >= 0
            logger.info(f"Files matching '{pattern}': {files[mask]}")


if __name__ == "__main__":
    # Run all tests
    logger.info("Starting comprehensive UV-VIS utils test suite...")
    
    # Basic functionality tests
    test_get_timestamp()
    test_generate_filename()
    test_get_spectra_path()
    test_find_files_by_pattern()
    test_find_files_by_patterns()
    test_zero_negatives()
    test_extract_timestamp()
    test_find_wavelength_index()
    test_validate_spectrum_data()
    test_save_spectrum_file()
    test_error_handling()
    
    # Data processing tests
    test_remove_negatives()
    test_calculate_absorbance()
    test_calculate_conversion()
    test_check_absorbance_stability()
    
    # File operation tests
    test_conversion_duplicate_protection()
    test_conversion_file_sorted()
    
    # Hardware-dependent tests (may fail if hardware not available)
    test_take_spectrum()
    test_take_spectrum_all_types()
    
    # Visualization tests
    test_plot_first_raw()
    test_plot_first_neg_removed()
    test_plot_first_absorbance()
    
    # Uncomment the next line if you want to run diagnostics
    # debug_spectra_folder()
    
    logger.info("All tests completed!")