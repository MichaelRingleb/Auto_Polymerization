"""
nmr_utils.py

Automated, robust NMR spectrum analysis utilities for polymerization monitoring.

This module provides a comprehensive workflow for NMR spectrum analysis, specifically designed
for monitoring polymerization reactions by quantifying monomer consumption relative to an
internal standard. The workflow includes:

Key Features:
- Baseline noise estimation with polynomial fit and type detection
- Peak finding in user-defined regions (monomer, standard) with connectivity testing
- Full peak integration using noise-level boundaries and robust numerical integration (Simpson's rule)
- Overlap detection to prevent double-counting of identical integration regions
- Batch processing of multiple spectra
- Publication-quality plotting with all key regions and methods annotated

Design Philosophy:
- Robust to noise: Uses noise-based thresholds rather than fixed parameters
- Adaptive: Automatically detects baseline type and adjusts integration boundaries
- Connected peaks: For standards, only integrates peaks connected to the main peak
- Overlap prevention: Detects and skips peaks with >90% overlapping integration regions
- Simpson's rule: Uses numerical integration for accurate area calculation

Author: Auto_Polymerization Team (with help of cursor ai)
Version: 0.1
"""

# --- Imports ---
import os
import numpy as np
from scipy.signal import find_peaks
from scipy.integrate import simpson
# Add pybaselines import
try:
    from pybaselines import Baseline
except ImportError:
    Baseline = None
    print("pybaselines not installed. Please install with 'pip install pybaselines'.")
from pathlib import Path
from datetime import datetime
from matterlab_nmr import NMR60Pro, DSolv, HSolv

# --- Hardware Control Utilities ---


def run_shimming(level=1):
    """
    Run shimming with the specified level (default: 1).
    This function calls the NMR60Pro hardware to perform shimming, which optimizes the magnetic field homogeneity.
    The 'level' parameter controls the number of shim parameters (e.g., 1=3, 2=8, 3=30),
    but the exact meaning depends on the hardware/firmware. Requires a connected NMR instrument.
    """
    nmr = NMR60Pro()
    nmr.shim(level)  # type: ignore
    print(f"Shimming complete with level {level}.")


def acquire_nmr_spectrum():
    """
    Acquire and save an NMR spectrum using hardlock experiment settings.
    This function configures the NMR60Pro for a hardlock experiment (no deuterated solvent lock),
    runs the acquisition, processes the 1D spectrum, and saves both the spectrum and raw data
    to Auto_Polymerization/users/data/NMR_data/<timestamp>.*
    Requires a connected NMR instrument and appropriate sample in the magnet.
    """
    nmr = NMR60Pro()
    nmr.set_hardlock_exp(
        num_scans=32,
        solvent=HSolv.DMSO,
        spectrum_center=5,
        spectrum_width=12
    )
    nmr.run()
    nmr.proc_1D()
    save_path = Path('Auto_Polymerization/users/data/NMR_data')
    save_path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nmr.save_spectrum(save_path, timestamp)
    nmr.save_data(save_path, timestamp)
    print(f"NMR data saved to {save_path / timestamp}")




def _create_annotation_text(x, y, text, color='black', fontsize=11, fontweight='bold', 
                           bbox_style='round,pad=0.3', bbox_alpha=0.9, zorder=10):
    """
    Helper function to create consistently styled text annotations.
    
    This function centralizes the text annotation styling to ensure consistency
    across all plot annotations and reduce code duplication.
    
    Parameters:
        x, y (float): Position coordinates
        text (str): Text to display
        color (str): Text color
        fontsize (int): Font size
        fontweight (str): Font weight ('normal', 'bold')
        bbox_style (str): Bbox style for background box
        bbox_alpha (float): Background box transparency
        zorder (int): Plotting order (higher = on top)
    
    Returns:
        matplotlib.text.Text: The created text object
    """
    import matplotlib.pyplot as plt
    return plt.text(x, y, text, color=color, ha='center', va='top', 
                   fontsize=fontsize, fontweight=fontweight,
                   bbox=dict(boxstyle=bbox_style, facecolor='white', alpha=bbox_alpha), 
                   zorder=zorder)

# --- Helper Functions ---

def _expand_peak_boundaries(spec, peak_idx, threshold, direction='both'):
    """
    Expand peak boundaries from a given peak index until the signal drops below a threshold.
    Used to determine integration limits for NMR peaks based on noise level.

    Parameters:
        spec (np.ndarray): Spectrum intensity values.
        peak_idx (int): Index of peak center.
        threshold (float): Intensity threshold for boundary detection (e.g., 3x noise).
        direction (str): 'left', 'right', or 'both' (expand in one or both directions).

    Returns:
        tuple: (left_bound, right_bound) indices in the spectrum array.
    Note:
        If the threshold is never crossed, the boundary will be at the spectrum edge.
    """
    left = peak_idx
    right = peak_idx
    # Expand left until below threshold or start of spectrum
    if direction in ['left', 'both']:
        while left > 0 and spec[left] > threshold:
            left -= 1
    # Expand right until below threshold or end of spectrum
    if direction in ['right', 'both']:
        while right < len(spec) - 1 and spec[right] > threshold:
            right += 1
    return left, right

# --- Core Analysis Functions ---

def integrate_monomer_peaks_simpson(
    ppm, spec_real, region, noise_std, snr_thresh=3, plot=False, annotate_peaks=None
):
    """
    Integrate the two largest monomer peaks in a specified region using Simpson's rule.
    Integration boundaries are determined by expanding from each peak until the signal drops below 3x the noise level.
    Overlap between integration regions is checked to avoid double-counting.

    Parameters:
        ppm (np.ndarray): Chemical shift axis (ppm).
        spec_real (np.ndarray): Real part of NMR spectrum.
        region (tuple): (min_ppm, max_ppm) for monomer peak region.
        noise_std (float): Standard deviation of baseline noise.
        snr_thresh (float): Signal-to-noise ratio threshold for peak detection.
        plot (bool): Whether to show debug plots.
        annotate_peaks (list): List to store peak annotation data.

    Returns:
        tuple: (peak_ppm, peak_intensity, total_integral, bounds, method, fallbacks)
            - peak_ppm: List of peak positions (ppm)
            - peak_intensity: List of peak intensities
            - total_integral: Sum of all peak integrals
            - bounds: List of (left, right) integration boundaries
            - method: Integration method used ('simpson')
            - fallbacks: List of fallback methods used (empty for this method)
    """
    mask = (ppm >= region[0]) & (ppm <= region[1])
    ppm_region = ppm[mask]
    spec_region = spec_real[mask]
    # Find all peaks above SNR threshold (robust to noise)
    height_thresh = snr_thresh * noise_std
    peaks, properties = find_peaks(spec_region, height=height_thresh)
    if len(peaks) == 0:
        print("[WARNING] No peaks found above threshold in monomer region")
        return None, None, 0.0, None, None, None
    # Sort peaks by intensity, descending
    peak_heights = spec_region[peaks]
    peak_indices = peaks[np.argsort(peak_heights)[::-1]]
    # Take the two largest peaks (or all if less than 2)
    n_peaks_to_integrate = min(2, len(peak_indices))
    selected_peaks = peak_indices[:n_peaks_to_integrate]
    full_indices = np.where(mask)[0]
    integrals = []
    bounds_list = []
    methods = []
    peak_ppms = []
    peak_intensities = []
    fallback_list = []
    # Use 3x noise threshold for integration boundaries (empirically robust)
    integration_threshold = 3 * noise_std
    for i, peak_idx in enumerate(selected_peaks):
        peak_ppm = ppm_region[peak_idx]
        peak_intensity = spec_region[peak_idx]
        peak_idx_full = full_indices[peak_idx]
        # Expand left/right from peak until below threshold
        left_bound = peak_idx
        right_bound = peak_idx
        for j in range(peak_idx, -1, -1):
            if spec_region[j] <= integration_threshold:
                left_bound = j
                break
        for j in range(peak_idx, len(spec_region)):
            if spec_region[j] <= integration_threshold:
                right_bound = j
                break
        # Convert to full spectrum indices
        left_full_idx = full_indices[left_bound]
        right_full_idx = full_indices[right_bound]
        # Check for overlap with previously integrated peaks
        # Overlap is defined as >90% of the current region overlapping with any previous region
        # This avoids double-counting nearly identical peaks 
        overlap_detected = False
        for prev_bounds in bounds_list:
            prev_left, prev_right = prev_bounds
            overlap_left = max(left_full_idx, prev_left)
            overlap_right = min(right_full_idx, prev_right)
            if overlap_left < overlap_right:  # There is overlap
                overlap_width = ppm[overlap_right] - ppm[overlap_left]
                current_width = ppm[right_full_idx] - ppm[left_full_idx]
                overlap_ratio = overlap_width / current_width
                if overlap_ratio > 0.9:  # More than 90% overlap (nearly identical regions)
                    print(f"[WARNING] Peak {i+1} at {peak_ppm:.3f} ppm has nearly identical integration region with previous peak (overlap ratio: {overlap_ratio:.2f}). Skipping to avoid double-counting.")
                    overlap_detected = True
                    break
        if overlap_detected:
            continue
        # Ensure we have a valid integration region
        if right_full_idx <= left_full_idx:
            print(f"[WARNING] Integration region for peak at {peak_ppm:.3f} ppm is empty. Skipping.")
            continue
        # Extract integration region for integration
        integration_ppm = ppm[left_full_idx:right_full_idx+1]
        integration_intensity = spec_region[left_bound:right_bound+1]
        # Use Simpson's rule for >=3 points, else fallback to trapezoidal
        if len(integration_intensity) >= 3:
            integral = float(simpson(integration_intensity, integration_ppm))
            method = 'simpson'
        else:
            integral = float(np.trapezoid(integration_intensity, integration_ppm))
            method = 'trapezoidal'
        integrals.append(integral)
        bounds_list.append((left_full_idx, right_full_idx))
        methods.append(method)
        peak_ppms.append(peak_ppm)
        peak_intensities.append(peak_intensity)
        fallback_list.append((method == 'trapezoidal', False))
    if not integrals:
        print("[WARNING] No valid integration regions found.")
        return None, None, 0.0, None, None, None
    # Sum integrals for total monomer signal
    total_integral = sum(integrals)
    # For plotting, annotate each peak
    if annotate_peaks is not None:
        annotate_peaks.clear()
        for i, (pp, pi, integ, bds, mth) in enumerate(zip(peak_ppms, peak_intensities, integrals, bounds_list, methods)):
            annotate_peaks.append({'ppm': pp, 'intensity': pi, 'integral': integ, 'bounds': bds, 'method': mth})
    return peak_ppms, peak_intensities, total_integral, bounds_list, methods, fallback_list

def find_peak_robust(
    ppm, spec_real, region, noise_std, snr_thresh=3, plot=False, annotate_peaks=None
):
    """
    Wrapper for integrate_monomer_peaks_simpson to maintain API consistency.
    Finds and integrates the two largest peaks in the monomer region using Simpson's rule
    with noise-based boundaries. Use this function for a consistent interface with other peak-finding routines.

    Parameters:
        ppm (np.ndarray): Chemical shift axis (ppm).
        spec_real (np.ndarray): Real part of NMR spectrum.
        region (tuple): (min_ppm, max_ppm) for monomer peak region.
        noise_std (float): Standard deviation of baseline noise.
        snr_thresh (float): Signal-to-noise ratio threshold for peak detection.
        plot (bool): Whether to show debug plots.
        annotate_peaks (list): List to store peak annotation data.

    Returns:
        tuple: (peak_ppm, peak_intensity, total_integral, bounds, method, fallbacks)
    """
    return integrate_monomer_peaks_simpson(
        ppm, spec_real, region, noise_std, snr_thresh, plot, annotate_peaks
    )


def characterize_baseline(ppm, spec, noise_region, max_order=3, improvement_thresh=0.05):
    """
    Estimate baseline noise and type by fitting polynomials of increasing order to a noise region.

    Parameters:
        ppm (np.ndarray): Chemical shift axis (ppm).
        spec (np.ndarray): NMR spectrum (complex or real).
        noise_region (tuple): (min_ppm, max_ppm) region for baseline fitting.
        max_order (int): Maximum polynomial order to try.
        improvement_thresh (float): Minimum relative std improvement to accept higher order.

    Returns:
        noise_std (float): Standard deviation of residuals after best fit.
        best_order (int): 0 (flat), 1 (sloped), 2 (curved), etc.
        x (np.ndarray): PPM values in noise region.
        baseline_fit (np.ndarray): Fitted baseline values in noise region.
    """
    if np.iscomplexobj(spec):
        spec_real = np.real(spec)
    else:
        spec_real = spec

    mask = (ppm >= noise_region[0]) & (ppm <= noise_region[1])
    x = ppm[mask]
    y = spec_real[mask]
    if len(x) < 2:
        return 1e-6, 0, x, y

    prev_std = np.std(y - np.mean(y))
    best_std = prev_std
    best_order = 0
    best_coeffs = [np.mean(y)]

    for order in range(1, max_order + 1):
        if len(x) < order + 1:
            break
        coeffs = np.polyfit(x, y, order)
        baseline = np.polyval(coeffs, x)
        resid = y - baseline
        resid_std = np.std(resid)
        if (prev_std - resid_std) / prev_std > improvement_thresh:
            best_std = resid_std
            best_order = order
            best_coeffs = coeffs
            prev_std = resid_std
        else:
            break
    baseline_fit = np.polyval(best_coeffs, x)
    return best_std, best_order, x, baseline_fit


def analyze_nmr_spectrum_with_auto_baseline_and_full_peak_integration(
    ppm, spec, monomer_region, std_region, noise_region, plot=True, title=None, save_plot=False, output_folder=None
):
    """
    Full automated NMR workflow for polymerization monitoring.
    
    This function implements a complete NMR analysis pipeline specifically designed for
    monitoring polymerization reactions. It quantifies monomer consumption relative to
    an internal standard using robust, noise-based methods.
    
    Workflow Steps:
    1. Baseline Characterization: Detects baseline type and estimates noise level
    2. ALS Baseline Correction: Applies asymmetric least squares baseline correction
    3. Monomer Peak Integration: Finds and integrates monomer peaks using Simpson's rule
    4. Standard Peak Integration: Integrates connected standard peaks with connectivity testing
    5. Overlap Detection: Prevents double-counting of identical integration regions
    6. Visualization: Creates publication-quality plots with annotations
    
    Key Design Decisions:
    - Uses 3× noise threshold for monomer peaks: Balances sensitivity with noise rejection
    - Uses 3.5× noise threshold for standard peaks: Higher threshold for more selective integration
    - 90% overlap threshold: Prevents double-counting while allowing distinct peaks
    - Connectivity testing for standards: Only integrates peaks connected to the main peak
    - Simpson's rule integration: Provides accurate numerical integration
    - Fixed ratio position at 4 ppm: Ensures consistent annotation placement

    Parameters:
        ppm (np.ndarray): Chemical shift axis (ppm).
        spec (np.ndarray): NMR spectrum (complex or real).
        monomer_region (tuple): (min_ppm, max_ppm) for monomer peak region.
        std_region (tuple): (min_ppm, max_ppm) for internal standard peak region.
        noise_region (tuple): (min_ppm, max_ppm) for baseline noise estimation.
        plot (bool): Whether to show the plot.
        title (str or None): Plot title (e.g., filename).
        save_plot (bool): Whether to save the plot to file.
        output_folder (str or None): Folder to save the plot. If None, uses current directory.

    Returns:
        dict: Results dictionary containing:
            - baseline_noise (float): Estimated noise standard deviation
            - baseline_type (int): Baseline type (0=flat, 1=sloped, 2=curved, etc.)
            - monomer_integral (float): Total monomer peak integral
            - std_integral (float): Total standard peak integral
            - integral_ratio (float): Monomer/Standard ratio
            - monomer_method (str): Integration method used for monomer
            - std_method (str): Integration method used for standard
    """
    # Baseline noise and type
    noise_std, baseline_type, noise_x, baseline_fit = characterize_baseline(ppm, spec, noise_region)
    baseline_type_str = ['flat', 'sloped', 'curved', 'higher-order'][baseline_type] if baseline_type < 4 else f'order-{baseline_type}'

    # Apply ALS baseline correction to the full spectrum
    spec_real = np.real(spec)
    if Baseline is not None:
        baseline_fitter = Baseline()
        als_baseline, _ = baseline_fitter.asls(spec_real, lam=1e5, p=0.001)
        spec_corrected = spec_real - als_baseline
    else:
        als_baseline = np.zeros_like(spec_real)
        spec_corrected = spec_real
        print("[WARNING] ALS baseline correction not applied (pybaselines not installed). Using raw spectrum.")

    # Monomer peak finding and integration - Simpson method only
    
    # For monomer, collect annotations for each singlet
    mono_annotations = []
    mono_result = find_peak_robust(
        ppm, spec_corrected, monomer_region, noise_std, snr_thresh=3, plot=plot, annotate_peaks=mono_annotations
    )
    if mono_result is not None:
        mono_peak_ppm, mono_peak_intensity, mono_integral, mono_bounds, mono_method, mono_fallbacks = mono_result
    else:
        mono_peak_ppm = mono_peak_intensity = mono_integral = mono_bounds = mono_method = mono_fallbacks = None

    # Standard region: peak finding + connectivity testing + Simpson's rule integration
    std_mask = (ppm >= std_region[0]) & (ppm <= std_region[1])
    ppm_std = ppm[std_mask]
    spec_std = spec_corrected[std_mask]
    std_integral = 0.0
    std_method = 'simpson_peaks_connected'
    std_peak_ppm = []
    std_bounds = []
    std_annotations = []
    
    if len(ppm_std) < 3:
        print("[WARNING] Not enough points for Simpson's rule in standard region.")
    else:
        from scipy.integrate import simpson
        
        noise_thresh = 3.5 * noise_std
        
        # Find all peaks above threshold
        peaks, properties = find_peaks(spec_std, height=noise_thresh)
        
        if len(peaks) == 0:
            print("[WARNING] No peaks found in standard region")
        else:
            # Sort peaks by intensity to find the main peak
            peak_heights = spec_std[peaks]
            sorted_indices = np.argsort(peak_heights)[::-1]  # Sort by height, descending
            main_peak_idx = peaks[sorted_indices[0]]
            main_peak_height = peak_heights[sorted_indices[0]]
            
            # Find the main peak's integration boundaries using helper function
            main_left, main_right = _expand_peak_boundaries(spec_std, main_peak_idx, noise_thresh, direction='both')
            
            # Test connectivity for other peaks
            connected_peaks = [main_peak_idx]  # Always include main peak
            connected_bounds = [(main_left, main_right)]
            
            for i in range(1, len(sorted_indices)):
                peak_idx = peaks[sorted_indices[i]]
                peak_height = peak_heights[sorted_indices[i]]
                peak_ppm = ppm_std[peak_idx]
                
                # Find this peak's boundaries using helper function
                peak_left, peak_right = _expand_peak_boundaries(spec_std, peak_idx, noise_thresh, direction='both')
                
                # Check connectivity with main peak
                # This ensures we only integrate peaks that are part of the same molecular structure
                # Peaks are considered connected if their integration regions overlap or are adjacent
                # This prevents integrating unrelated peaks that happen to be in the same region
                is_connected = False
                for main_bound in connected_bounds:
                    # Check if this peak overlaps or is adjacent to any connected region
                    if (peak_left <= main_bound[1] and peak_right >= main_bound[0]):
                        is_connected = True
                        break
                
                if is_connected:
                    connected_peaks.append(peak_idx)
                    connected_bounds.append((peak_left, peak_right))
                    
                                        # Merge overlapping bounds
                    merged_bounds = []
                    for bound in connected_bounds:
                        if not merged_bounds:
                            merged_bounds.append(bound)
                        else:
                            # Check if this bound overlaps with the last merged bound
                            last_bound = merged_bounds[-1]
                            if bound[0] <= last_bound[1] + 1:  # +1 for adjacent regions
                                # Merge bounds
                                merged_bounds[-1] = (min(last_bound[0], bound[0]), max(last_bound[1], bound[1]))
                            else:
                                merged_bounds.append(bound)
                    connected_bounds = merged_bounds
            
            # Integrate all connected regions
            for i, (left, right) in enumerate(connected_bounds):
                if right > left:
                    area = float(simpson(spec_std[left:right+1], ppm_std[left:right+1]))
                    std_integral += area
                    
                    # Find the peak center in this region
                    region_peaks = [p for p in connected_peaks if left <= p <= right]
                    if region_peaks:
                        center_peak = region_peaks[np.argmax([spec_std[p] for p in region_peaks])]
                        center_ppm = ppm_std[center_peak]
                    else:
                        center_ppm = ppm_std[(left + right) // 2]
                    
                    std_peak_ppm.append(center_ppm)
                    std_bounds.append((left, right))
                    std_annotations.append({
                        'ppm': center_ppm, 
                        'integral': area, 
                        'bounds': (left, right), 
                        'method': std_method,
                        'connected': True
                    })

    # Console output - removed since we removed all info prints

    # Plotting
    if plot:
        import matplotlib.pyplot as plt
        plt.figure(figsize=(10,5))
        plt.plot(ppm, spec_real, label='Raw spectrum', zorder=1)
        if noise_x is not None and len(noise_x) > 1:
            plt.axvspan(noise_x.min(), noise_x.max(), color='gray', alpha=0.12, label='Noise estimation region', zorder=0)
            plt.plot(noise_x, baseline_fit, color='black', lw=2, label='Baseline fit', zorder=3)
        # Plot ALS baseline on full spectrum
        if als_baseline is not None:
            plt.plot(ppm, als_baseline, color='magenta', lw=2, alpha=0.8, label='ALS baseline correction', zorder=3)
        # Shade the actual integrated range for monomer peaks (on raw spectrum)
        monomer_annotation_data = []
        if mono_peak_ppm is not None and isinstance(mono_peak_ppm, (list, tuple, np.ndarray)) and len(mono_annotations) > 0:
            for i, p in enumerate(mono_peak_ppm):
                if i < len(mono_annotations):
                    center = mono_annotations[i]['ppm']
                    integral = mono_annotations[i]['integral']
                    method = mono_annotations[i]['method']
                    
                    # Simpson method uses actual bounds
                    bounds = mono_annotations[i]['bounds']
                    if bounds is not None:
                        left = ppm[bounds[0]]
                        right = ppm[bounds[1]]
                        label_text = 'Monomer peaks' if i==0 else None
                        color = 'blue'
                    else:
                        continue
                    
                    if left < right:
                        plt.axvspan(left, right, color=color, alpha=0.3, label=label_text, zorder=2)
                        # Store annotation data for later
                        monomer_annotation_data.append({
                            'center': center, 'integral': integral, 'color': color
                        })
        
        # Shade the standard peak integration region in orange
        std_annotation_data = []
        if std_method == 'simpson_peaks_connected' and len(std_bounds) > 0:
            for i, (left, right) in enumerate(std_bounds):
                label_text = 'Standard peaks' if i==0 else None
                
                # Convert from standard region indices to full spectrum ppm values
                full_indices = np.where((ppm >= std_region[0]) & (ppm <= std_region[1]))[0]
                left_full = full_indices[left]
                right_full = full_indices[right]
                
                plt.axvspan(ppm[left_full], ppm[right_full], color='orange', alpha=0.25, label=label_text, zorder=2)
                center = std_annotations[i]['ppm']
                area = std_annotations[i]['integral']
                
                # Store annotation data for later
                std_annotation_data.append({
                    'center': center, 'integral': area, 'color': 'orange'
                })
        # Noise threshold and noise level lines (superimposed on raw spectrum)
        if (noise_std is not None and ppm is not None and hasattr(ppm, '__len__') and len(ppm) > 0
            and (isinstance(ppm, (np.ndarray, list)) or hasattr(ppm, '__iter__'))):
            y_noise3 = als_baseline + float(noise_std) * 3 if als_baseline is not None else float(noise_std) * 3
            y_noise1 = als_baseline + float(noise_std) if als_baseline is not None else float(noise_std)
            plt.plot(ppm, y_noise3,
                     color='red', linestyle=':', alpha=0.9, lw=2, label='Peak detection threshold (3× noise)', zorder=5)
            plt.plot(ppm, y_noise1,
                     color='purple', linestyle='--', alpha=0.7, lw=1.5, label='1× noise level', zorder=5)
        plt.xlabel('Chemical shift (ppm)')
        plt.ylabel('Intensity')
        plt.title(title if title else 'NMR Spectrum Analysis')
        # Scale y-axis so tallest monomer peak is at half the plot height above the baseline at that peak
        if mono_peak_ppm is not None and isinstance(mono_peak_ppm, (list, tuple, np.ndarray)) and len(mono_peak_ppm) > 0:
            tallest = 0
            baseline_at_peak = 0
            for p in mono_peak_ppm:
                idx = np.argmin(np.abs(ppm - p))
                val = spec_real[idx] - als_baseline[idx]
                if val > tallest:
                    tallest = val
                    baseline_at_peak = als_baseline[idx]
            if tallest > 0:
                plt.ylim(baseline_at_peak, baseline_at_peak + 2 * tallest)
        plt.legend(loc='best')
        plt.gca().invert_xaxis()
        
        # Add peak integral annotations after plot limits are set
        y_min, y_max = plt.ylim()
        y_range = y_max - y_min
        
        # Add total monomer integral annotation (if multiple peaks, show sum)
        if len(monomer_annotation_data) > 0:
            total_monomer_integral = sum(annotation['integral'] for annotation in monomer_annotation_data)
            # Position at the center of all monomer peaks
            monomer_centers = [annotation['center'] for annotation in monomer_annotation_data]
            avg_center = np.mean(monomer_centers)
            y_annot = y_min - y_range * 0.08  # Position below the plot
            
            # Add monomer integral annotation using helper function
            _create_annotation_text(avg_center, y_annot, f"∫={total_monomer_integral:.1f}", 
                                   color='blue', fontsize=11, fontweight='bold')
            
            # Calculate and add ratio annotation at fixed position below 4 ppm
            if len(std_annotation_data) > 0:
                total_std_integral = sum(annotation['integral'] for annotation in std_annotation_data)
                if total_std_integral > 0:
                    ratio = total_monomer_integral / total_std_integral
                    # Position ratio at fixed location below 4 ppm
                    # Fixed positioning ensures consistent placement across all plots
                    # 4 ppm is chosen as it's typically outside the monomer and standard regions
                    # This makes the ratio easy to find and compare across different spectra
                    ratio_x = 4.0  # Fixed position at 4 ppm for consistent placement
                    _create_annotation_text(ratio_x, y_annot, f"ratio: {ratio:.3f}", 
                                           color='black', fontsize=10, fontweight='normal',
                                           bbox_style='round,pad=0.2', bbox_alpha=0.8)
        
        # Add standard peak annotations using helper function
        for annotation in std_annotation_data:
            y_annot = y_min - y_range * 0.08  # Position below the plot
            _create_annotation_text(annotation['center'], y_annot, f"∫={annotation['integral']:.1f}", 
                                   color=annotation['color'], fontsize=11, fontweight='bold')
        
        plt.tight_layout()
        
        # Save plot if requested
        if save_plot:
            if output_folder is None:
                output_folder = os.getcwd()
            
            # Create filename from title with _integrated_spec suffix
            if title:
                filename = f"{title}_integrated_spec.png"
            else:
                filename = "nmr_spectrum_integrated_spec.png"
            
            # Ensure output folder exists
            os.makedirs(output_folder, exist_ok=True)
            
            # Save plot (will overwrite existing files)
            plot_path = os.path.join(output_folder, filename)
            plt.savefig(plot_path, dpi=300, bbox_inches='tight')
            print(f"Plot saved to: {plot_path}")
            
            # Save integral values to text file (tabular format)
            txt_filename = "nmr_integration_results.txt"
            txt_path = os.path.join(output_folder, txt_filename)
            
            # Calculate total integrals
            total_monomer_integral = 0.0
            total_std_integral = 0.0
            
            if len(monomer_annotation_data) > 0:
                total_monomer_integral = sum(annotation['integral'] for annotation in monomer_annotation_data)
            
            if len(std_annotation_data) > 0:
                total_std_integral = sum(annotation['integral'] for annotation in std_annotation_data)
            
            # Calculate ratio
            ratio = total_monomer_integral / total_std_integral if total_std_integral > 0 else None
            ratio_str = f"{ratio:.6f}" if ratio is not None else "N/A"
            
            # Ratio = Monomer_Integral / Standard_Integral
            # Write to text file (append mode)
            filename = title if title else "unknown"
            # Prepare monomer peak positions as a string (leftmost only)
            if mono_peak_ppm is not None and hasattr(mono_peak_ppm, '__iter__') and len(mono_peak_ppm) > 0:
                leftmost_peak = min(mono_peak_ppm)
                monomer_peak_positions_str = f"{leftmost_peak:.3f}"
            elif mono_peak_ppm is not None:
                monomer_peak_positions_str = f"{mono_peak_ppm:.3f}"
            else:
                monomer_peak_positions_str = ""
            # Check if file exists to determine if we need to write headers and to avoid duplicate filenames
            file_exists = os.path.exists(txt_path)
            existing_filenames = set()
            if file_exists:
                with open(txt_path, 'r') as f:
                    for line in f:
                        if line.strip() == '' or line.startswith('Filename'):
                            continue
                        existing_filenames.add(line.split('\t')[0])
            if filename in existing_filenames:
                print(f"Filename '{filename}' already present in {txt_path}, skipping write.")
            else:
                with open(txt_path, 'a') as f:
                    # Write headers if file is new
                    if not file_exists:
                        f.write("Filename\tMonomer_Start\tMonomer_End\tMonomer_Peak_Positions\tMonomer_Integral\tStandard_Start\tStandard_End\tStandard_Integral\tRatio(Monomer/Standard)\n")
                    # Write data row
                    f.write(f"{filename}\t{monomer_region[0]:.2f}\t{monomer_region[1]:.2f}\t{monomer_peak_positions_str}\t{total_monomer_integral:.6f}\t{std_region[0]:.2f}\t{std_region[1]:.2f}\t{total_std_integral:.6f}\t{ratio_str}\n")
                print(f"Integration results appended to: {txt_path}")
        
        plt.show()

    return {
        'baseline_noise': noise_std,
        'baseline_type': baseline_type,
        'monomer_integral': mono_integral,
        'std_integral': std_integral,
        'integral_ratio': mono_integral / std_integral if (mono_integral is not None and std_integral not in (None, 0)) else None,
        'monomer_method': mono_method,
        'std_method': std_method
    }

# --- Batch and Post-Processing Utilities ---

def batch_analyze_nmr_folder(folder, monomer_region, std_region, noise_region, plot=True, save_plots=True):
    """
    Batch analyze all NMR spectra in a folder using the automated workflow.
    Expects .npy files for both ppm and spectrum, named as {base}_freq_ppm.npy and {base}_spec.npy.
    Results are saved in tabular format and plots are optionally saved for each spectrum.
    Any missing or malformed files are skipped with a warning.

    Parameters:
        folder (str): Path to folder containing NMR .npy files.
        monomer_region (tuple): (min_ppm, max_ppm) for monomer peak region.
        std_region (tuple): (min_ppm, max_ppm) for internal standard peak region.
        noise_region (tuple): (min_ppm, max_ppm) for baseline noise estimation.
        plot (bool): Whether to show plots for each spectrum.
        save_plots (bool): Whether to save plots to the same folder as the data.

    Returns:
        list of dict: List of result dictionaries, one per spectrum. Each dict contains:
            - filename (str): Base filename of the spectrum
            - baseline_noise (float): Estimated noise standard deviation
            - baseline_type (int): Baseline type (0=flat, 1=sloped, 2=curved, etc.)
            - monomer_integral (float): Total monomer peak integral
            - std_integral (float): Total standard peak integral
            - integral_ratio (float): Monomer/Standard ratio
            - monomer_method (str): Integration method used for monomer
            - std_method (str): Integration method used for standard
    """
    files = os.listdir(folder)
    base_names = sorted(set(f.split('_freq_ppm.npy')[0] for f in files if f.endswith('_freq_ppm.npy')))
    results = []
    for base in base_names:
        ppm = np.load(os.path.join(folder, base + '_freq_ppm.npy'))
        spec = np.load(os.path.join(folder, base + '_spec.npy'))
        res = analyze_nmr_spectrum_with_auto_baseline_and_full_peak_integration(
            ppm, spec, monomer_region, std_region, noise_region, 
            plot=plot, title=base, save_plot=save_plots, output_folder=folder
        )
        results.append({'filename': base, **res})
    return results

def monomer_removal_dialysis(
    integration_txt_path,
    nmr_data_folder,
    noise_region=(9, 10),
    ppm_suffix='_freq_ppm.npy',
    spec_suffix='_spec.npy',
):
    """
    Analyze monomer removal after dialysis by checking the height at the leftmost monomer peak position
    (as recorded in the integration txt) relative to the noise level in the NMR spectrum.
    Outliers and missing files are skipped with a warning. The height/noise ratio is a proxy for residual monomer.

    Parameters:
        integration_txt_path (str): Path to nmr_integration_results.txt
        nmr_data_folder (str): Folder containing the NMR .npy files
        noise_region (tuple): (min_ppm, max_ppm) for noise estimation
        ppm_suffix (str): Suffix for ppm axis files
        spec_suffix (str): Suffix for spectrum files

    Returns:
        List[dict]: Each dict contains filename, leftmost_monomer_peak_ppm, peak_height, noise_level, ratio
    """
    import numpy as np
    import os
    results = []
    # Read integration results
    with open(integration_txt_path, 'r') as f:
        header = f.readline()
        colnames = [c.strip() for c in header.strip().split('\t')]
        for line in f:
            if not line.strip():
                continue
            fields = line.strip().split('\t')
            entry = dict(zip(colnames, fields))
            filename = entry['Filename']
            try:
                leftmost_peak_ppm = float(entry['Monomer_Peak_Positions'])
            except Exception:
                continue
            # Load NMR data
            ppm_path = os.path.join(nmr_data_folder, filename + ppm_suffix)
            spec_path = os.path.join(nmr_data_folder, filename + spec_suffix)
            if not (os.path.exists(ppm_path) and os.path.exists(spec_path)):
                print(f"Missing NMR data for {filename}, skipping.")
                continue
            ppm = np.load(ppm_path)
            spec = np.load(spec_path)
            if np.iscomplexobj(spec):
                spec_real = np.real(spec)
            else:
                spec_real = spec
            # Find index closest to leftmost peak position
            idx = np.argmin(np.abs(ppm - leftmost_peak_ppm))
            peak_height = spec_real[idx]
            # Estimate noise in noise_region
            noise_mask = (ppm >= noise_region[0]) & (ppm <= noise_region[1])
            if not np.any(noise_mask):
                print(f"No data in noise region for {filename}, skipping.")
                continue
            noise_level = np.std(spec_real[noise_mask])
            ratio = peak_height / noise_level if noise_level > 0 else np.nan
            results.append({
                'Filename': filename,
                'Leftmost_Monomer_Peak_PPM': leftmost_peak_ppm,
                'Peak_Height': peak_height,
                'Noise_Level': noise_level,
                'Height/Noise_Ratio': ratio
            })
    # Print summary table
    if results:
        print("\nMonomer Removal Dialysis Results:")
        print("Filename\tLeftmost_Peak_PPM\tPeak_Height\tNoise_Level\tHeight/Noise_Ratio")
        for r in results:
            print(f"{r['Filename']}\t{r['Leftmost_Monomer_Peak_PPM']:.3f}\t{r['Peak_Height']:.4g}\t{r['Noise_Level']:.4g}\t{r['Height/Noise_Ratio']:.3f}")
    else:
        print("No valid results found.")
    return results

def analyze_dialysis_conversion(
    integration_txt_path,
    nmr_data_folder,
    spectrum_base,
    noise_region=(9, 10),
    ppm_suffix='_freq_ppm.npy',
    spec_suffix='_spec.npy',
    search_window=0.2,
    output_txt='dialysis_conversion.txt'
):
    """
    Analyze dialysis conversion by finding the median leftmost monomer peak position (from integration txt),
    searching for a peak near that position in a new spectrum, and reporting peak intensity and noise.
    Outliers are removed using the IQR method. The result is written to a tabular text file.

    Parameters:
        integration_txt_path (str): Path to nmr_integration_results.txt
        nmr_data_folder (str): Folder containing the NMR .npy files
        spectrum_base (str): Base filename for the new spectrum (without suffix)
        noise_region (tuple): (min_ppm, max_ppm) for noise estimation
        ppm_suffix (str): Suffix for ppm axis files
        spec_suffix (str): Suffix for spectrum files
        search_window (float): Window (in ppm) around the median peak to search for a peak
        output_txt (str): Output file for results
    """
    import numpy as np
    import os
    # 1. Read all leftmost monomer peak positions from integration results
    leftmost_peaks = []
    with open(integration_txt_path, 'r') as f:
        header = f.readline()
        colnames = [c.strip() for c in header.strip().split('\t')]
        for line in f:
            if not line.strip():
                continue
            fields = line.strip().split('\t')
            entry = dict(zip(colnames, fields))
            try:
                pos = float(entry['Monomer_Peak_Positions'])
                leftmost_peaks.append(pos)
            except Exception:
                continue
    if not leftmost_peaks:
        print("No valid leftmost monomer peak positions found in integration results.")
        return None
    # 2. Remove outliers using IQR (robust to extreme values)
    q1 = np.percentile(leftmost_peaks, 25)
    q3 = np.percentile(leftmost_peaks, 75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    filtered_peaks = [p for p in leftmost_peaks if lower <= p <= upper]
    if not filtered_peaks:
        filtered_peaks = leftmost_peaks  # fallback if all are outliers
    # 3. Calculate median of filtered peaks
    median_peak = float(np.median(filtered_peaks))
    # 4. Load new spectrum and search for a peak near the median position
    ppm_path = os.path.join(nmr_data_folder, spectrum_base + ppm_suffix)
    spec_path = os.path.join(nmr_data_folder, spectrum_base + spec_suffix)
    if not (os.path.exists(ppm_path) and os.path.exists(spec_path)):
        print(f"Missing NMR data for {spectrum_base}, aborting.")
        return None
    ppm = np.load(ppm_path)
    spec = np.load(spec_path)
    if np.iscomplexobj(spec):
        spec_real = np.real(spec)
    else:
        spec_real = spec
    # 5. Search for a peak within ±search_window ppm of median_peak
    mask = (ppm >= median_peak - search_window) & (ppm <= median_peak + search_window)
    if not np.any(mask):
        print(f"No data in search window for {spectrum_base}.")
        return None
    from scipy.signal import find_peaks
    region_spec = spec_real[mask]
    region_ppm = ppm[mask]
    # Baseline estimate: use minimum in the window
    baseline = np.min(region_spec)
    # Find peaks (height relative to baseline)
    peaks, properties = find_peaks(region_spec - baseline)
    if len(peaks) == 0:
        print(f"No peak found near median position for {spectrum_base}.")
        found_peak_ppm = np.nan
        peak_intensity = np.nan
    else:
        # Take the highest peak
        max_idx = peaks[np.argmax(region_spec[peaks])]
        found_peak_ppm = region_ppm[max_idx]
        peak_intensity = region_spec[max_idx] - baseline
    # 6. Estimate noise in noise_region
    noise_mask = (ppm >= noise_region[0]) & (ppm <= noise_region[1])
    if not np.any(noise_mask):
        print(f"No data in noise region for {spectrum_base}.")
        return None
    noise_level = np.std(spec_real[noise_mask])
    # 7. Check if peak is above 2x noise (significant)
    pass_fail = (peak_intensity > 2 * noise_level) if not np.isnan(peak_intensity) else False
    # 8. Write results to output_txt (tabular, append mode)
    output_path = os.path.join(nmr_data_folder, output_txt)
    file_exists = os.path.exists(output_path)
    with open(output_path, 'a') as f:
        if not file_exists:
            f.write("Filename\tMedian_Peak_PPM\tFound_Peak_PPM\tPeak_Intensity\tNoise\tAbove_2x_Noise\n")
        f.write(f"{spectrum_base}\t{median_peak:.3f}\t{found_peak_ppm:.3f}\t{peak_intensity:.6f}\t{noise_level:.6f}\t{int(pass_fail)}\n")
    print(f"\nDialysis conversion analysis for {spectrum_base}:")
    print(f"Median peak position: {median_peak:.3f} ppm")
    print(f"Found peak position: {found_peak_ppm:.3f} ppm")
    print(f"Peak intensity: {peak_intensity:.6f}")
    print(f"Noise: {noise_level:.6f}")
    print(f"Above 2x noise: {'YES' if pass_fail else 'NO'}")
    return {
        'Filename': spectrum_base,
        'Median_Peak_PPM': median_peak,
        'Found_Peak_PPM': found_peak_ppm,
        'Peak_Intensity': peak_intensity,
        'Noise': noise_level,
        'Above_2x_Noise': pass_fail
    }

# --- Main/Test Block ---
if __name__ == "__main__":
    # Example: batch process all spectra in a folder
    folder = r"C:\Users\xo37lay\source\repos\Auto_Polymerization\Auto_Polymerization\src\NMR\example_data_MMA_and_standard"
    monomer_region = (5, 6.5)
    std_region = (6.5, 8)
    noise_region = (9, 10)  # Set to a region with no peaks
    batch_analyze_nmr_folder(folder, monomer_region, std_region, noise_region, plot=True, save_plots=True)