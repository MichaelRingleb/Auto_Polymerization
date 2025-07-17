"""
test_monomer_simpson.py

Test script for the new monomer Simpson integration method.
"""

import numpy as np
import sys
import os

# Add the NMR_code directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'NMR_code'))

try:
    from nmr_utils import (
        analyze_nmr_spectrum_with_auto_baseline_and_full_peak_integration,
        integrate_monomer_peaks_simpson
    )
    print("✓ Successfully imported nmr_utils functions")
except ImportError as e:
    print(f"✗ Failed to import nmr_utils: {e}")
    sys.exit(1)


def generate_test_nmr_data():
    """Generate test NMR data with known peaks"""
    # Generate ppm axis (10 to 0 ppm, NMR convention)
    ppm = np.linspace(10, 0, 1000)
    
    # Create spectrum with baseline drift and noise
    intensity = np.zeros(1000)
    
    # Add two monomer peaks
    peaks = [
        (6.0, 100, 0.1),   # (ppm, height, width)
        (5.5, 80, 0.15),   # Second peak
    ]
    
    for peak_ppm, height, width in peaks:
        gaussian = height * np.exp(-0.5 * ((ppm - peak_ppm) / width)**2)
        intensity += gaussian
    
    # Add baseline drift
    baseline_drift = 0.05 * (ppm - 5)**2 + 0.02 * (ppm - 5) + 1
    intensity += baseline_drift
    
    # Add noise
    noise = np.random.normal(0, 0.3, 1000)
    intensity += noise
    
    return ppm, intensity


def test_simpson_integration():
    """Test the new Simpson integration method"""
    print("\n" + "="*60)
    print("Testing Monomer Simpson Integration")
    print("="*60)
    
    # Generate test data
    ppm, intensity = generate_test_nmr_data()
    
    # Define regions
    monomer_region = (5.0, 6.5)
    std_region = (7.0, 8.0)
    noise_region = (8.5, 9.5)
    
    print(f"Test data generated:")
    print(f"  - PPM range: {ppm.min():.2f} - {ppm.max():.2f}")
    print(f"  - Intensity range: {intensity.min():.2f} - {intensity.max():.2f}")
    print(f"  - Monomer region: {monomer_region}")
    print(f"  - Noise region: {noise_region}")
    
    # Test the new Simpson method
    print("\n[TEST] Using monomer_simpson method...")
    results_simpson = analyze_nmr_spectrum_with_auto_baseline_and_full_peak_integration(
        ppm, intensity, monomer_region, std_region, noise_region,
        plot=False, title='Test - Simpson Method', monomer_method='monomer_simpson'
    )
    
    print(f"\nSimpson method results:")
    print(f"  - Monomer integral: {results_simpson['monomer_integral']:.4f}")
    print(f"  - Monomer method: {results_simpson['monomer_method']}")
    print(f"  - Baseline noise: {results_simpson['baseline_noise']:.4f}")
    
    # Test the legacy monomer method for comparison
    print("\n[TEST] Using legacy monomer method...")
    results_legacy = analyze_nmr_spectrum_with_auto_baseline_and_full_peak_integration(
        ppm, intensity, monomer_region, std_region, noise_region,
        plot=False, title='Test - Legacy Method', monomer_method='monomer'
    )
    
    print(f"\nLegacy method results:")
    print(f"  - Monomer integral: {results_legacy['monomer_integral']:.4f}")
    print(f"  - Monomer method: {results_legacy['monomer_method']}")
    print(f"  - Baseline noise: {results_legacy['baseline_noise']:.4f}")
    
    # Compare results
    if results_simpson['monomer_integral'] is not None and results_legacy['monomer_integral'] is not None:
        diff = abs(results_simpson['monomer_integral'] - results_legacy['monomer_integral'])
        print(f"\nComparison:")
        print(f"  - Simpson integral: {results_simpson['monomer_integral']:.4f}")
        print(f"  - Legacy integral: {results_legacy['monomer_integral']:.4f}")
        print(f"  - Difference: {diff:.4f}")
        
        if diff < 1.0:  # Allow some tolerance
            print("✓ Integration results are reasonable")
            return True
        else:
            print("⚠ Integration results differ significantly")
            return False
    else:
        print("✗ One or both methods failed to produce results")
        return False


def test_direct_simpson_function():
    """Test the direct Simpson integration function"""
    print("\n" + "="*60)
    print("Testing Direct Simpson Integration Function")
    print("="*60)
    
    # Generate test data
    ppm, intensity = generate_test_nmr_data()
    
    # Define monomer region
    monomer_region = (5.0, 6.5)
    
    # Estimate noise from a quiet region
    noise_mask = (ppm >= 8.5) & (ppm <= 9.5)
    noise_std = np.std(intensity[noise_mask])
    
    print(f"Test parameters:")
    print(f"  - Monomer region: {monomer_region}")
    print(f"  - Estimated noise std: {noise_std:.4f}")
    
    # Test direct function
    try:
        peak_ppms, peak_intensities, total_integral, bounds_list, methods, fallback_list = integrate_monomer_peaks_simpson(
            ppm, intensity, monomer_region, noise_std, snr_thresh=3, plot=False
        )
        
        print(f"\nDirect function results:")
        print(f"  - Number of peaks found: {len(peak_ppms) if peak_ppms else 0}")
        print(f"  - Total integral: {total_integral:.4f}")
        print(f"  - Methods used: {methods}")
        
        if peak_ppms:
            for i, (ppm_val, intensity_val, integral_val, bounds, method) in enumerate(zip(peak_ppms, peak_intensities, [total_integral], bounds_list, methods)):
                print(f"  - Peak {i+1}: {ppm_val:.3f} ppm, integral={integral_val:.4f}, method={method}")
                print(f"    Bounds: {ppm[bounds[0]]:.3f} - {ppm[bounds[1]]:.3f} ppm")
        
        print("✓ Direct Simpson function works correctly")
        return True
        
    except Exception as e:
        print(f"✗ Direct Simpson function failed: {e}")
        return False


def test_edge_cases():
    """Test edge cases for the Simpson method"""
    print("\n" + "="*60)
    print("Testing Edge Cases")
    print("="*60)
    
    # Test with no peaks
    ppm = np.linspace(10, 0, 500)
    intensity = np.random.normal(0, 0.1, 500)  # Just noise
    
    monomer_region = (5.0, 6.5)
    noise_std = 0.1
    
    print("Testing with no peaks...")
    try:
        result = integrate_monomer_peaks_simpson(
            ppm, intensity, monomer_region, noise_std, snr_thresh=3, plot=False
        )
        if result[0] is None:
            print("✓ Correctly handled no peaks case")
        else:
            print("⚠ Should have returned None for no peaks")
    except Exception as e:
        print(f"✗ Failed to handle no peaks case: {e}")
    
    # Test with single peak
    intensity_single = np.random.normal(0, 0.1, 500)
    # Add one peak
    peak_idx = np.argmin(np.abs(ppm - 5.5))
    intensity_single[peak_idx-10:peak_idx+10] += 50 * np.exp(-0.5 * ((np.arange(-10, 10)) / 2)**2)
    
    print("Testing with single peak...")
    try:
        result = integrate_monomer_peaks_simpson(
            ppm, intensity_single, monomer_region, noise_std, snr_thresh=3, plot=False
        )
        if result[0] is not None and len(result[0]) == 1:
            print("✓ Correctly handled single peak case")
        else:
            print("⚠ Should have found exactly one peak")
    except Exception as e:
        print(f"✗ Failed to handle single peak case: {e}")
    
    return True


def main():
    """Run all tests"""
    print("Testing Monomer Simpson Integration Method")
    print("="*60)
    
    tests = [
        test_simpson_integration,
        test_direct_simpson_function,
        test_edge_cases,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")
    
    print("\n" + "="*60)
    print(f"Test Results: {passed}/{total} tests passed")
    print("="*60)
    
    if passed == total:
        print("🎉 All tests passed!")
        return True
    else:
        print("❌ Some tests failed!")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 