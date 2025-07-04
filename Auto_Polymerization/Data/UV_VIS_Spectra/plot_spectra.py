# -*- coding: utf-8 -*-

import os
import glob
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict
import re

from numpy.__config__ import show

# --- Helper Functions ---

def load_spectrum(file):
    """Load a spectrum file and return (x, y) or (None, None) if invalid."""
    try:
        data = np.loadtxt(file, comments='#', delimiter=None)
        if data.ndim < 2 or data.shape[1] < 2:
            print(f"Skipping {file}: not enough columns.")
            return None, None
        return data[:, 0], data[:, 1]
    except Exception as e:
        print(f"Fehler beim Laden von {file}: {e}")
        return None, None

def save_spectrum(filename, x, y, header):
    """Save spectrum data to a file. Overwrites if file exists."""
    # Overwrite existing file without prompt
    np.savetxt(filename, np.column_stack((x, y)), fmt="%.6f", header=header)
    print(f"File saved (overwritten if existed): {filename}")

def plot_spectra(spectra_list, xlabel, ylabel, title):
    plt.figure(figsize=(10, 6))
    for x, y, label in spectra_list:
        plt.plot(x, y, label=label)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.legend(fontsize='small', loc='best')
    plt.grid(True)
    plt.tight_layout()
    plt.show()

# --- Main Functions ---

def plot_spectra_from_folder(folder_path):
    spectra_dir = folder_path
    print(spectra_dir)
    txt_files = glob.glob(os.path.join(spectra_dir, "*.txt"))
    print("Gefundene Spektren:", txt_files)
    spectra_list = []
    for file in txt_files:
        x, y = load_spectrum(file)
        if x is not None and y is not None:
            spectra_list.append((x, y, os.path.basename(file)))
    plot_spectra(spectra_list, "Wavelength (nm)", "Intensity (a.u.)", "Alle Spektren aus TXT-Dateien")

def average_spectra_in_folder(folder):
    txt_files = glob.glob(os.path.join(folder, "*.txt"))
    if not txt_files:
        print("No spectra found in", folder)
        return
    groups = defaultdict(list)
    for file in txt_files:
        basename = os.path.basename(file)
        match = re.match(r"(.+?)(?=_[0-9])", basename)
        if match:
            prefix = match.group(0)
        else:
            prefix = os.path.splitext(basename)[0]
        groups[prefix].append(file)
    for prefix, files in groups.items():
        spectra = []
        x_ref = None
        for file in files:
            x, y = load_spectrum(file)
            if x is None or y is None:
                continue
            if x_ref is None:
                x_ref = x
            elif not np.allclose(x, x_ref):
                print(f"Skipping {file}: x-axis mismatch.")
                continue
            spectra.append(y)
        if spectra and x_ref is not None:
            y_avg = np.mean(spectra, axis=0)
            avg_filename = os.path.join(folder, f"{prefix}_average.txt")
            save_spectrum(avg_filename, x_ref, y_avg, "Wavelength\tAverage Intensity")

def reference_averaged_spectra_to_dmso(folder, dmso_prefix="pure_DMSO_spectrum"):
    avg_files = glob.glob(os.path.join(folder, "*_average.txt"))
    dmso_file = None
    for f in avg_files:
        if os.path.basename(f).startswith(dmso_prefix):
            dmso_file = f
            break
    if not dmso_file:
        print(f"DMSO reference file with prefix '{dmso_prefix}' not found.")
        return
    x_dmso, y_dmso = load_spectrum(dmso_file)
    for avg_file in avg_files:
        if avg_file == dmso_file:
            continue
        x, y = load_spectrum(avg_file)
        if x is None or y is None or not np.allclose(x, x_dmso):
            print(f"Skipping {avg_file}: x-axis mismatch with DMSO reference.")
            continue
        y_diff = y - y_dmso
        out_name = os.path.splitext(avg_file)[0] + "_referenced_to_DMSO.txt"
        save_spectrum(out_name, x, y_diff, "Wavelength\tIntensity diff (sample - DMSO)")

def calculate_and_plot_absorbance(
    sample_folder,
    ref_spectrum_path
):
    """
    Calculates and plots absorbance spectra for all spectra in sample_folder,
    using the given reference spectrum (e.g., DMSO).
    """
    if not os.path.exists(ref_spectrum_path):
        print(f"Reference file '{ref_spectrum_path}' not found.")
        return
    x_ref, I0 = load_spectrum(ref_spectrum_path)
    if x_ref is None or I0 is None:
        print("Reference spectrum could not be loaded.")
        return
    I0[I0 <= 0] = 1e-6
    sample_files = [
        f for f in glob.glob(os.path.join(sample_folder, "*.txt"))
        if os.path.isfile(f)
        and not f.endswith("_average.txt")
        and not f.endswith("_absorbance.txt")
    ]
    spectra_list = []
    for sample_file in sample_files:
        x, I = load_spectrum(sample_file)
        if x is None or I is None or not np.allclose(x, x_ref):
            print(f"Skipping {sample_file}: wavelength axis mismatch.")
            continue
        I[I <= 0] = 1e-6
        absorbance = np.log10(I0 / I)
        spectra_list.append((x, absorbance, os.path.basename(sample_file)))
        out_name = os.path.splitext(sample_file)[0] + "_absorbance.txt"
        save_spectrum(out_name, x, absorbance, "Wavelength\tAbsorbance")
    plot_spectra(spectra_list, "Wavelength (nm)", "Absorbance (A)", "Absorbance Spectra (referenced to DMSO)")

def calculate_and_plot_absorbance_for_all_spectra(
    sample_folder,
    ref_folder,
    ref_filename="pure_DMSO_spectrum_average.txt"
):
    ref_path = os.path.join(ref_folder, ref_filename)
    if not os.path.exists(ref_path):
        print(f"Reference file '{ref_path}' not found.")
        return
    x_ref, I0 = load_spectrum(ref_path)
    if x_ref is None or I0 is None:
        print("Reference spectrum could not be loaded.")
        return
    I0[I0 <= 0] = 1e-6
    sample_files = [
        f for f in glob.glob(os.path.join(sample_folder, "*.txt"))
        if os.path.isfile(f)
    ]
    spectra_list = []
    for sample_file in sample_files:
        x, I = load_spectrum(sample_file)
        if x is None or I is None or not np.allclose(x, x_ref):
            print(f"Skipping {sample_file}: wavelength axis mismatch.")
            continue
        I[I <= 0] = 1e-6
        absorbance = np.log10(I0 / I)
        spectra_list.append((x, absorbance, os.path.basename(sample_file)))
        out_name = os.path.splitext(sample_file)[0] + "_absorbance.txt"
        save_spectrum(out_name, x, absorbance, "Wavelength\tAbsorbance")
    plot_spectra(spectra_list, "Wavelength (nm)", "Absorbance (A)", "Absorbance Spectra (referenced to DMSO)")

if __name__ == "__main__":
    # Example usage:
    #plot_spectra_from_folder(r"C:\Users\xo37lay\source\repos\Auto_Polymerization\Auto_Polymerization\Spectra\MRG-061-G- spectra_G1_G2_after_aminolysis")
    # average_spectra_in_folder(r"C:\Users\xo37lay\source\repos\Auto_Polymerization\Auto_Polymerization\Spectra\pure_compounds_spectra_test")
    # reference_averaged_spectra_to_dmso(r"C:\Users\xo37lay\source\repos\Auto_Polymerization\Auto_Polymerization\Spectra\pure_compounds_spectra_test")
    calculate_and_plot_absorbance(r"C:\Users\xo37lay\source\repos\Auto_Polymerization\Auto_Polymerization\Spectra\MRG-061-F5_spectra_while_stopped_with_alu_foil", 
                                  r"C:\Users\xo37lay\source\repos\Auto_Polymerization\Auto_Polymerization\Spectra\MRG-061-F-3_pure_compounds_spectra_test\pure_DMSO_spectrum_average.txt")
    # calculate_and_plot_absorbance(r"C:\Users\xo37lay\source\repos\Auto_Polymerization\Auto_Polymerization\Spectra\pure_compounds_spectra_test")
    # calculate_and_plot_absorbance_for_all_spectra(
    #     sample_folder=r"C:\Users\xo37lay\source\repos\Auto_Polymerization\Auto_Polymerization\Spectra\spectra_while_stopped",
    #     ref_folder=r"C:\Users\xo37lay\source\repos\Auto_Polymerization\Auto_Polymerization\Spectra\pure_compounds_spectra_test"
    # )