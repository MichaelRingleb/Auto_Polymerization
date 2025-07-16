"""
nmr_utils.py

Automated, robust NMR spectrum analysis utilities for:
- Baseline noise estimation (with polynomial fit and type detection)
- Peak finding in user-defined regions (monomer, standard)
- Full peak integration using noise-level boundaries and robust numerical integration (Simpson/trapezoidal)
- Batch processing of multiple spectra
- Publication-quality plotting with all key regions and methods annotated

Author: [Your Name]
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from scipy.integrate import simpson
import datetime

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

def robust_integral(y, x):
    """
    Integrate y(x) using Simpson's rule if possible, otherwise fall back to trapezoidal rule.

    Parameters:
        y (np.ndarray): Intensity values.
        x (np.ndarray): PPM values.

    Returns:
        integral (float): Integrated area.
        method (str): 'simpson' or 'trapezoidal'.
    """
    if len(y) < 3:
        return float(np.trapezoid(y, x)), 'trapezoidal'
    else:
        return float(simpson(y, x)), 'simpson'

def find_integration_bound_windowed(y, threshold, peak_idx, direction='left', window=3):
    """
    Find the index where the signal drops to (or below) the noise threshold on one side of the peak,
    using a rolling window to smooth out fluctuations. If not found, return the region boundary.
    """
    n = len(y)
    if direction == 'left':
        indices = range(peak_idx, -1, -1)
    else:
        indices = range(peak_idx, n)
    for i in indices:
        w_start = max(i - window // 2, 0)
        w_end = min(i + window // 2 + 1, n)
        window_vals = y[w_start:w_end]
        if np.all(window_vals <= threshold):
            return i, False  # Found crossing
    # Not found, return region edge
    return indices[-1], True

def expand_integration_bounds(y, peak_idx, noise_std, max_gap=5):
    """
    Expand integration bounds left/right from peak_idx until the signal stays below noise_std for max_gap consecutive points, or until array edge.
    Returns (left_idx, right_idx).
    """
    n = len(y)
    # Expand left
    left = peak_idx
    below_count = 0
    for i in range(peak_idx, 0, -1):
        if abs(y[i]) < noise_std:
            below_count += 1
            if below_count >= max_gap:
                left = i + max_gap - 1
                break
        else:
            below_count = 0
    # Expand right
    right = peak_idx
    below_count = 0
    for i in range(peak_idx, n):
        if abs(y[i]) < noise_std:
            below_count += 1
            if below_count >= max_gap:
                right = i - max_gap + 1
                break
        else:
            below_count = 0
    return left, right


def find_peak_robust(
    ppm, spec_real, region, noise_std, snr_thresh=3, window=3, baseline_order=1, baseline_iter=3, plot=False, max_gap=5, mode='auto', annotate_peaks=None
):
    """
    For 'monomer' mode: Integrate each detected singlet separately, sum integrals, annotate each.
    For 'standard' mode: Use hybrid approach (all peaks, expand to baseline, integrate as one region).
    """
    mask = (ppm >= region[0]) & (ppm <= region[1])
    ppm_region = ppm[mask]
    spec_region = spec_real[mask]
    print(f"[DEBUG] Region: {region}, Points: {len(ppm_region)}, Noise std: {noise_std:.4g}")
    height_thresh = snr_thresh * noise_std
    print(f"[DEBUG] SNR threshold: {height_thresh:.4g}")
    peaks, _ = find_peaks(spec_region, height=height_thresh)
    print(f"[DEBUG] Peaks found: {peaks}")
    if len(peaks) == 0:
        print("[DEBUG] No peaks found above threshold.")
        return None, None, None, None, None, None
    full_indices = np.where(mask)[0]
    if mode == 'monomer':
        # Integrate each singlet separately
        integrals = []
        bounds_list = []
        methods = []
        peak_ppms = []
        peak_intensities = []
        fallback_list = []
        for peak_idx in peaks:
            peak_ppm = ppm_region[peak_idx]
            peak_intensity = spec_region[peak_idx]
            peak_idx_full = full_indices[peak_idx]
            ppm_local, spec_corr, baseline_fit, left_full, right_full = iterative_local_baseline_correction(
                ppm, spec_real, peak_idx_full, initial_window_pts=40, edge_frac=0.15, order=baseline_order, max_iter=baseline_iter, noise_std=noise_std, plot=plot
            )
            local_n = len(ppm_local)
            peak_idx_local = np.argmin(np.abs(ppm_local - ppm[peak_idx_full]))
            # Expand left
            left = peak_idx_local
            below_count = 0
            for i in range(peak_idx_local, 0, -1):
                if abs(spec_corr[i]) < noise_std:
                    below_count += 1
                    if below_count >= max_gap:
                        left = i + max_gap - 1
                        break
                else:
                    below_count = 0
            # Expand right
            right = peak_idx_local
            below_count = 0
            for i in range(peak_idx_local, local_n):
                if abs(spec_corr[i]) < noise_std:
                    below_count += 1
                    if below_count >= max_gap:
                        right = i - max_gap + 1
                        break
                else:
                    below_count = 0
            left_full_idx = left_full + left
            right_full_idx = left_full + right
            if right_full_idx <= left_full_idx:
                print(f"[WARNING] Integration region for peak at {peak_ppm:.3f} ppm is empty. Skipping.")
                continue
            integral, method = robust_integral(spec_corr[left:right+1], ppm_local[left:right+1])
            print(f"[DEBUG] Integrated area for peak at {peak_ppm:.3f} ppm: {integral:.4f} using {method}")
            integrals.append(integral)
            bounds_list.append((left_full_idx, right_full_idx))
            methods.append(method)
            peak_ppms.append(peak_ppm)
            peak_intensities.append(peak_intensity)
            fallback_list.append((False, False))
        if not integrals:
            return None, None, 0.0, (None, None), 'none', None
        # Sum integrals for total monomer signal
        total_integral = sum(integrals)
        # For plotting, annotate each singlet
        if annotate_peaks is not None:
            annotate_peaks.clear()
            for i, (pp, pi, integ, bds, mth) in enumerate(zip(peak_ppms, peak_intensities, integrals, bounds_list, methods)):
                annotate_peaks.append({'ppm': pp, 'intensity': pi, 'integral': integ, 'bounds': bds, 'method': mth})
        # Return total, but also provide details for plotting
        return peak_ppms, peak_intensities, total_integral, bounds_list, methods, fallback_list
    else:
        # Standard: hybrid approach as before
        leftmost_peak = peaks.min() if hasattr(peaks, 'min') else min(peaks)
        rightmost_peak = peaks.max() if hasattr(peaks, 'max') else max(peaks)
        peak_idx = peaks[np.argmax(spec_region[peaks])]
        peak_ppm = ppm_region[peak_idx]
        peak_intensity = spec_region[peak_idx]
        leftmost_full = full_indices[leftmost_peak]
        rightmost_full = full_indices[rightmost_peak]
        expand_pts = 10
        left_init = max(0, leftmost_full - expand_pts)
        right_init = min(len(ppm) - 1, rightmost_full + expand_pts)
        peak_idx_full = full_indices[peak_idx]
        ppm_local, spec_corr, baseline_fit, left_full, right_full = iterative_local_baseline_correction(
            ppm, spec_real, peak_idx_full, initial_window_pts=max(right_init - left_init, 40) // 2, edge_frac=0.15, order=baseline_order, max_iter=baseline_iter, noise_std=noise_std, plot=plot
        )
        local_n = len(ppm_local)
        left_local = np.argmin(np.abs(ppm_local - ppm[leftmost_full]))
        right_local = np.argmin(np.abs(ppm_local - ppm[rightmost_full]))
        n = len(spec_corr)
        left = left_local
        below_count = 0
        for i in range(left_local, 0, -1):
            if abs(spec_corr[i]) < noise_std:
                below_count += 1
                if below_count >= max_gap:
                    left = i + max_gap - 1
                    break
            else:
                below_count = 0
        right = right_local
        below_count = 0
        for i in range(right_local, n):
            if abs(spec_corr[i]) < noise_std:
                below_count += 1
                if below_count >= max_gap:
                    right = i - max_gap + 1
                    break
            else:
                below_count = 0
        left_full_idx = left_full + left
        right_full_idx = left_full + right
        if right_full_idx <= left_full_idx:
            print("[WARNING] Integration region is empty or only one point. No integration performed.")
            return peak_ppm, peak_intensity, 0.0, (left_full_idx, right_full_idx), 'none', (False, False)
        integral, method = robust_integral(spec_corr[left:right+1], ppm_local[left:right+1])
        print(f"[DEBUG] Integrated area: {integral:.4f} using {method}")
        return peak_ppm, peak_intensity, integral, (left_full_idx, right_full_idx), method, (False, False)

def iterative_local_baseline_correction(ppm, spec, peak_idx, initial_window_pts=40, edge_frac=0.15, order=1, max_iter=3, noise_std=None, frac_height=0.05, min_pts=5, plot=False):
    """
    Iteratively fit and subtract a local baseline around a peak.
    - Start with a window around the peak.
    - Fit a polynomial baseline to the edges (excluding the peak region).
    - Subtract baseline, find new peak edges, and repeat.
    Returns corrected signal, baseline fit, and diagnostics.
    """
    n = len(spec)
    left = max(0, peak_idx - initial_window_pts)
    right = min(n, peak_idx + initial_window_pts + 1)
    for it in range(max_iter):
        ppm_local = ppm[left:right]
        spec_local = spec[left:right]
        n_edge = int(len(spec_local) * edge_frac)
        # Use edges for baseline
        baseline_x = np.concatenate([ppm_local[:n_edge], ppm_local[-n_edge:]])
        baseline_y = np.concatenate([spec_local[:n_edge], spec_local[-n_edge:]])
        coeffs = np.polyfit(baseline_x, baseline_y, order)
        baseline_fit = np.polyval(coeffs, ppm_local)
        spec_corr = spec_local - baseline_fit
        # Find new peak edges on baseline-corrected signal
        peak_height = spec_corr[peak_idx - left]
        # Use SNR or fractional height
        threshold = 0
        if noise_std is not None:
            threshold = max(noise_std, frac_height * peak_height)
        else:
            threshold = frac_height * peak_height
        # Left edge
        new_left = peak_idx - left
        for i in range(peak_idx - left, 0, -1):
            if spec_corr[i] < threshold:
                new_left = i
                break
        # Right edge
        new_right = peak_idx - left
        for i in range(peak_idx - left, len(spec_corr)):
            if spec_corr[i] < threshold:
                new_right = i
                break
        # Ensure minimum width
        if (peak_idx - left - new_left) < min_pts:
            new_left = max(0, peak_idx - left - min_pts)
        if (new_right - (peak_idx - left)) < min_pts:
            new_right = min(len(spec_corr) - 1, peak_idx - left + min_pts)
        # Convert to global indices
        left = max(0, left + new_left - n_edge)
        right = min(n, left + (new_right - new_left) + 2 * n_edge)
        # Stop if region doesn't change
        if it > 0 and abs(new_right - new_left) < min_pts * 2:
            break
    # Final fit for output
    ppm_local = ppm[left:right]
    spec_local = spec[left:right]
    n_edge = int(len(spec_local) * edge_frac)
    baseline_x = np.concatenate([ppm_local[:n_edge], ppm_local[-n_edge:]])
    baseline_y = np.concatenate([spec_local[:n_edge], spec_local[-n_edge:]])
    coeffs = np.polyfit(baseline_x, baseline_y, order)
    baseline_fit = np.polyval(coeffs, ppm_local)
    spec_corr = spec_local - baseline_fit
    if plot:
        import matplotlib.pyplot as plt
        plt.figure(figsize=(8,4))
        plt.plot(ppm_local, spec_local, label='Raw local signal')
        plt.plot(ppm_local, baseline_fit, label='Baseline fit', lw=2)
        plt.plot(ppm_local, spec_corr, label='Baseline-corrected', lw=2)
        plt.axvline(ppm[peak_idx], color='k', linestyle='--', label='Peak max')
        plt.xlabel('ppm')
        plt.ylabel('Intensity')
        plt.title('Iterative Local Baseline Correction')
        plt.legend()
        plt.gca().invert_xaxis()
        plt.tight_layout()
        plt.show()
    return ppm_local, spec_corr, baseline_fit, left, right

def analyze_nmr_spectrum_with_auto_baseline_and_full_peak_integration(
    ppm, spec, monomer_region, std_region, noise_region, plot=True, title=None
):
    """
    Full automated NMR workflow:
      1. Baseline noise and type detection (characterize_baseline)
      2. Peak finding in monomer and std regions (find_peak_robust)
      3. Integration using noise-level boundaries and robust numerical integration
      4. Console output and publication-quality plotting

    Parameters:
        ppm (np.ndarray): Chemical shift axis (ppm).
        spec (np.ndarray): NMR spectrum (complex or real).
        monomer_region (tuple): (min_ppm, max_ppm) for monomer peak.
        std_region (tuple): (min_ppm, max_ppm) for internal standard peak.
        noise_region (tuple): (min_ppm, max_ppm) for baseline noise estimation.
        plot (bool): Whether to show the plot.
        title (str or None): Plot title (e.g., filename).

    Returns:
        dict: Results including integrals, baseline noise, type, and methods.
    """
    # Baseline noise and type
    noise_std, baseline_type, noise_x, baseline_fit = characterize_baseline(ppm, spec, noise_region)
    baseline_type_str = ['flat', 'sloped', 'curved', 'higher-order'][baseline_type] if baseline_type < 4 else f'order-{baseline_type}'
    print(f"Baseline noise std: {noise_std:.4f}, Baseline type: {baseline_type_str}")

    # Peak finding and integration
    spec_real = np.real(spec)
    # For monomer, collect annotations for each singlet
    mono_annotations = []
    mono_result = find_peak_robust(
        ppm, spec_real, monomer_region, noise_std, snr_thresh=3, plot=plot, max_gap=5, mode='monomer', annotate_peaks=mono_annotations
    )
    std_result = find_peak_robust(
        ppm, spec_real, std_region, noise_std, snr_thresh=3, plot=plot, max_gap=5, mode='standard'
    )
    # Unpack monomer result
    if mono_result is not None:
        mono_peak_ppm, mono_peak_intensity, mono_integral, mono_bounds, mono_method, mono_fallbacks = mono_result
    else:
        mono_peak_ppm = mono_peak_intensity = mono_integral = mono_bounds = mono_method = mono_fallbacks = None
    # Unpack standard result
    if std_result is not None:
        std_peak_ppm, std_peak_intensity, std_integral, std_bounds, std_method, std_fallbacks = std_result
    else:
        std_peak_ppm = std_peak_intensity = std_integral = std_bounds = std_method = std_fallbacks = None

    # Console output
    if mono_peak_ppm is not None:
        if isinstance(mono_bounds, list):
            for i, (mono_left, mono_right) in enumerate(mono_bounds):
                fwhm_ppm = abs(ppm[mono_left] - ppm[mono_right])
                integral = mono_annotations[i]['integral'] if i < len(mono_annotations) else mono_integral
                method = mono_annotations[i]['method'] if i < len(mono_annotations) else mono_method
                ppm_val = mono_peak_ppm[i] if isinstance(mono_peak_ppm, (list, tuple)) else mono_peak_ppm
                print(f"Monomer singlet {i+1} at {ppm_val:.3f} ppm: Integration width = {fwhm_ppm:.4f} ppm, Integral = {integral:.2f} (method: {method})")
        else:
            mono_left, mono_right = mono_bounds
            fwhm_ppm = abs(ppm[mono_left] - ppm[mono_right])
            print(f"Monomer peak at {mono_peak_ppm:.3f} ppm: Integration width = {fwhm_ppm:.4f} ppm, Integral = {mono_integral:.2f} (method: {mono_method})")
    else:
        print("Monomer peak not found")
        mono_left = mono_right = None
        mono_method = None

    if std_peak_ppm is not None:
        std_left, std_right = std_bounds
        fwhm_ppm = abs(ppm[std_left] - ppm[std_right])
        print(f"Std peak at {std_peak_ppm:.3f} ppm: Integration width = {fwhm_ppm:.4f} ppm, Integral = {std_integral:.2f} (method: {std_method})")
    else:
        print("Std peak not found")
        std_left = std_right = None
        std_method = None

    if mono_integral is not None and std_integral not in (None, 0):
        ratio = mono_integral / std_integral
        print(f"Integral ratio (Monomer/Std): {ratio:.3f}")
    else:
        ratio = None
        print("Integral ratio (Monomer/Std): N/A")

    # Plotting
    if plot:
        plt.figure(figsize=(10,5))
        plt.plot(ppm, spec_real, label='Spectrum', zorder=1)
        if noise_x is not None and len(noise_x) > 1:
            plt.axvspan(noise_x.min(), noise_x.max(), color='gray', alpha=0.12, label='Noise region', zorder=0)
            plt.plot(noise_x, baseline_fit, color='black', lw=2, label='Baseline fit (noise region)', zorder=3)
        # Integration regions and bounds
        def plot_bounds(bounds, color, label, fallback, peak_ppm=None, peak_intensity=None, integral=None, method=None):
            if bounds is None or fallback is None:
                return
            if isinstance(bounds[0], (list, tuple)):
                # Multiple regions (for monomer singlets)
                for i, b in enumerate(bounds):
                    l, r = b
                    plt.axvspan(float(ppm[l]), float(ppm[r]), color=color, alpha=0.2, label=label if i==0 else None, zorder=2)
                    plt.axvline(float(ppm[l]), color=color, linestyle=':', lw=1.5, zorder=4)
                    plt.axvline(float(ppm[r]), color=color, linestyle=':', lw=1.5, zorder=4)
            else:
                left, right = bounds
                plt.axvspan(float(ppm[left]), float(ppm[right]), color=color, alpha=0.2, label=label, zorder=2)
                plt.axvline(float(ppm[left]), color=color, linestyle=':', lw=1.5, zorder=4)
                plt.axvline(float(ppm[right]), color=color, linestyle=':', lw=1.5, zorder=4)
            if peak_ppm is not None:
                if isinstance(peak_ppm, (list, tuple)):
                    for i, pp in enumerate(peak_ppm):
                        plt.axvline(float(pp), color=color, linestyle='--', lw=1.5, zorder=4)
                else:
                    plt.axvline(float(peak_ppm), color=color, linestyle='--', lw=1.5, zorder=4)
            if (peak_ppm is not None and peak_intensity is not None and integral is not None and method is not None):
                if isinstance(peak_ppm, (list, tuple)) and 'mono_annotations' in locals() and mono_annotations is not None:
                    for ann in mono_annotations:
                        plt.annotate(f'Area: {ann["integral"]:.2f}\n({ann["method"]})',
                                     xy=(float(ann['ppm']), float(ann['intensity'])),
                                     xytext=(float(ann['ppm']), float(ann['intensity']) * 1.05),
                                     color=color, fontsize=10,
                                     arrowprops=dict(arrowstyle='->', color=color, lw=1.2))
                else:
                    plt.annotate(f'Area: {integral:.2f}\n({method})',
                                 xy=(float(peak_ppm), float(peak_intensity)),
                                 xytext=(float(peak_ppm), float(peak_intensity) * 1.05),
                                 color=color, fontsize=10,
                                 arrowprops=dict(arrowstyle='->', color=color, lw=1.2))
        if mono_bounds is not None and mono_fallbacks is not None and mono_bounds[0] is not None and mono_bounds[1] is not None and hasattr(mono_fallbacks, '__iter__'):
            plot_bounds(mono_bounds, 'blue', f'Monomer integration ({mono_method if isinstance(mono_method, str) else "simpson"})', mono_fallbacks, mono_peak_ppm, mono_peak_intensity, mono_integral, mono_method)
        if std_bounds is not None and std_fallbacks is not None and std_bounds[0] is not None and std_bounds[1] is not None and hasattr(std_fallbacks, '__iter__'):
            plot_bounds(std_bounds, 'green', f'Std integration ({std_method})', std_fallbacks, std_peak_ppm, std_peak_intensity, std_integral, std_method)
        # Noise threshold and noise level lines (superimposed on spectrum)
        if (noise_std is not None and ppm is not None and hasattr(ppm, '__len__') and len(ppm) > 0
            and (isinstance(ppm, (np.ndarray, list)) or hasattr(ppm, '__iter__'))):
            y_noise3 = float(noise_std) * 3
            y_noise1 = float(noise_std)
            plt.plot(ppm, np.full_like(ppm, y_noise3),
                     color='red', linestyle=':', alpha=0.9, lw=2, label='3× noise threshold', zorder=5)
            plt.plot(ppm, np.full_like(ppm, y_noise1),
                     color='purple', linestyle='--', alpha=0.7, lw=1.5, label='Noise level (1× std)', zorder=5)
        plt.xlabel('ppm')
        plt.ylabel('Intensity (real)')
        plt.title(title if title else 'NMR Spectrum: Robust Peak Integration to Noise Level')
        # Scale y-axis so monomer peak is at ~60% of ymax
        if mono_peak_ppm is not None and mono_peak_intensity not in (None, 0):
            if isinstance(mono_peak_intensity, (list, tuple)):
                plt.ylim(0, max(mono_peak_intensity) / 0.6)
            else:
                plt.ylim(0, mono_peak_intensity / 0.6)
        plt.legend(loc='best')
        plt.gca().invert_xaxis()
        plt.tight_layout()
        plt.show()

    return {
        'baseline_noise': noise_std,
        'baseline_type': baseline_type,
        'monomer_integral': mono_integral,
        'std_integral': std_integral,
        'integral_ratio': ratio,
        'monomer_method': mono_method,
        'std_method': std_method
    }

def batch_analyze_nmr_folder(folder, monomer_region, std_region, noise_region, plot=True):
    """
    Analyze all spectra in a folder using the automated workflow.

    Parameters:
        folder (str): Path to folder containing NMR .npy files.
        monomer_region (tuple): (min_ppm, max_ppm) for monomer peak.
        std_region (tuple): (min_ppm, max_ppm) for internal standard peak.
        noise_region (tuple): (min_ppm, max_ppm) for baseline noise estimation.
        plot (bool): Whether to show plots.

    Returns:
        list of dict: Results for each spectrum.
    """
    files = os.listdir(folder)
    base_names = sorted(set(f.split('_freq_ppm.npy')[0] for f in files if f.endswith('_freq_ppm.npy')))
    results = []
    for base in base_names:
        ppm = np.load(os.path.join(folder, base + '_freq_ppm.npy'))
        spec = np.load(os.path.join(folder, base + '_spec.npy'))
        print(f"\n===== {base} =====")
        res = analyze_nmr_spectrum_with_auto_baseline_and_full_peak_integration(
            ppm, spec, monomer_region, std_region, noise_region, plot=plot, title=base
        )
        results.append({'filename': base, **res})
    return results

if __name__ == "__main__":
    # Example: batch process all spectra in a folder
    folder = r"C:\Users\xo37lay\source\repos\Auto_Polymerization\Auto_Polymerization\src\NMR_code\example_data_MMA_and_standard"
    monomer_region = (5, 6.5)
    std_region = (6.5, 8)
    noise_region = (9, 10)  # Set to a region with no peaks
    batch_analyze_nmr_folder(folder, monomer_region, std_region, noise_region, plot=True)