import os
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from scipy.integrate import simps


def load_nmr_data(directory):
    """
    Loads NMR data from .npy files in a directory.

    Returns:
        List of tuples: (filename, ppm_array, intensity_array)
    """
    data = []
    files = os.listdir(directory)
    base_names = set(f.split('_freq_ppm.npy')[0] for f in files if f.endswith('_freq_ppm.npy'))
    for base in base_names:
        try:
            ppm = np.load(os.path.join(directory, base + '_freq_ppm.npy'))
            spec = np.load(os.path.join(directory, base + '_spec.npy'))
            if ppm.shape != spec.shape:
                print(f"❌ Skipping {base}: shape mismatch")
                continue
            data.append((base, ppm, spec))
        except Exception as e:
            print(f"❌ Error loading {base}: {e}")
    return data


def calculate_baseline_noise(ppm, spec, noise_region=(-1, 1)):
    """
    Estimates baseline noise as the standard deviation in a flat ppm region.

    Args:
        ppm: 1D array of ppm values
        spec: 1D array of intensities
        noise_region: Tuple of (min, max) ppm region

    Returns:
        Baseline noise (standard deviation)
    """
    mask = (ppm >= noise_region[0]) & (ppm <= noise_region[1])
    return np.std(spec[mask]) if np.any(mask) else 1e-6


def find_peak(ppm, spec, region, noise_std, snr_thresh=5, peak_width=0.05):
    """
    Finds the highest peak in a ppm region above an SNR threshold and integrates its area.

    Args:
        ppm: ppm array
        spec: intensity array
        region: tuple (min_ppm, max_ppm)
        noise_std: baseline noise standard deviation
        snr_thresh: signal-to-noise threshold to detect peak
        peak_width: integration window half-width in ppm

    Returns:
        peak_ppm, peak_intensity, integrated_area, snr
    """
    mask = (ppm >= region[0]) & (ppm <= region[1])
    ppm_region = ppm[mask]
    spec_region = spec[mask]

    height_thresh = snr_thresh * noise_std
    peaks, props = find_peaks(spec_region, height=height_thresh)

    if not len(peaks):
        return None, None, 0, 0

    idx = peaks[np.argmax(props['peak_heights'])]
    peak_ppm = ppm_region[idx]
    peak_intensity = spec_region[idx]

    # Integrate area ±peak_width around peak ppm
    int_mask = (ppm >= peak_ppm - peak_width) & (ppm <= peak_ppm + peak_width)
    area = simps(spec[int_mask], ppm[int_mask])
    snr = peak_intensity / noise_std if noise_std > 0 else np.nan

    return peak_ppm, peak_intensity, area, snr


def safe_ratio(num, denom):
    """Compute ratio safely, return nan if denom is zero or None."""
    if denom in (0, None, np.nan):
        return np.nan
    return num / denom


def plot_spectrum(ppm, spec, monomer_ppm, std_ppm, noise_std, snr_thresh, mono_height):
    """
    Plots the spectrum with y-axis scaled so monomer peak is at 50% of y-axis max.

    Args:
        ppm, spec: data arrays
        monomer_ppm: monomer peak location (ppm)
        std_ppm: internal standard peak location (ppm)
        noise_std: baseline noise std
        snr_thresh: SNR threshold used
        mono_height: monomer peak intensity
    """
    if mono_height is None or mono_height == 0:
        print("⚠️ Cannot scale plot, monomer peak intensity is zero or None.")
        return

    y_max = mono_height / 0.5  # monomer peak scaled to 50% y axis

    plt.figure(figsize=(8, 4))
    plt.plot(ppm, spec, label='Raw Spectrum')
    if monomer_ppm:
        plt.axvline(monomer_ppm, color='blue', linestyle='--', label='Monomer Peak')
    if std_ppm:
        plt.axvline(std_ppm, color='green', linestyle='--', label='Internal Std Peak')
    plt.axhline(noise_std * snr_thresh, color='red', linestyle=':', label='SNR Threshold')
    plt.title(f"Spectrum (Monomer Peak at 50% Y-axis)")
    plt.xlabel("ppm")
    plt.ylabel("Intensity")
    plt.ylim(0, y_max)
    plt.legend()
    plt.gca().invert_xaxis()
    plt.tight_layout()
    plt.show()


def process_spectra_auto(directory, monomer_range, std_range, snr_thresh=5, noise_region=(-1, 1), plot=True):
    """
    Automatically detect peaks and analyze spectra in a directory.

    Args:
        directory (str): Folder containing spectra files
        monomer_range (tuple): Rough ppm range to find monomer peak
        std_range (tuple): Rough ppm range to find internal standard peak
        snr_thresh (float): Minimum SNR threshold for peak detection
        noise_region (tuple): ppm range to estimate baseline noise
        plot (bool): Whether to plot the spectra

    Returns:
        List of dicts with analysis results
    """
    results = []
    spectra = load_nmr_data(directory)

    for fname, ppm, spec in spectra:
        noise_std = calculate_baseline_noise(ppm, spec, noise_region)

        mono_ppm, mono_int, mono_area, mono_snr = find_peak(ppm, spec, monomer_range, noise_std, snr_thresh)
        std_ppm, std_int, std_area, std_snr = find_peak(ppm, spec, std_range, noise_std, snr_thresh)

        result = {
            'filename': fname,
            'baseline_noise': noise_std,
            'monomer_ppm': mono_ppm,
            'monomer_intensity': mono_int,
            'monomer_area': mono_area,
            'monomer_snr': mono_snr,
            'std_ppm': std_ppm,
            'std_intensity': std_int,
            'std_area': std_area,
            'std_snr': std_snr,
            'area_ratio': safe_ratio(mono_area, std_area),
            'intensity_ratio': safe_ratio(mono_int, std_int)
        }
        results.append(result)

        print(f"\n📄 {fname}")
        print(f"  Baseline noise (std): {noise_std:.4f}")
        print(f"  Monomer peak: {mono_ppm} ppm | Intensity: {mono_int:.2f} | Area: {mono_area:.2f} | SNR: {mono_snr:.1f}")
        print(f"  Internal Std peak: {std_ppm} ppm | Intensity: {std_int:.2f} | Area: {std_area:.2f} | SNR: {std_snr:.1f}")
        print(f"  Area ratio (Mono/Std): {result['area_ratio']:.2f}")
        print(f"  Intensity ratio (Mono/Std): {result['intensity_ratio']:.2f}")

        if plot:
            plot_spectrum(ppm, spec, mono_ppm, std_ppm, noise_std, snr_thresh, mono_int)

    return results


if __name__ == "__main__":
    folder = "D:\Aspuru-Guzik Lab Dropbox\Lab Manager Aspuru-Guzik\PythonScript\Han\NanalysisNMR\nmr\examples"  # ⬅️ Change this to your spectra folder
    monomer_search_range = (5.5, 6.5)
    internal_std_range = (6.5, 8)
    snr_threshold = 5

    process_spectra_auto(
        directory=folder,
        monomer_range=monomer_search_range,
        std_range=internal_std_range,
        snr_thresh=snr_threshold,
        plot=True
    )
