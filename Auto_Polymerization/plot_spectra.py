# -*- coding: utf-8 -*-

import os
import glob
import numpy as np
import matplotlib.pyplot as plt



def plot_spectra_from_Spectra_folder():
    # Nur im Ordner "spectra" suchen, nicht in Unterordnern
    spectra_dir = os.path.join(os.path.dirname(__file__), "spectra")
    txt_files = glob.glob(os.path.join(spectra_dir, "*.txt"))  # kein "**", also keine Unterordner

    print("Gefundene Spektren:", txt_files)

    plt.figure(figsize=(10, 6))

    for file in txt_files:
        try:
            data = np.loadtxt(file, comments='#', delimiter=None)
            if data.ndim < 2 or data.shape[1] < 2:
                continue
            x = data[:, 0]
            y = data[:, 1]
            plt.plot(x, y, label=os.path.basename(file))
        except Exception as e:
            print(f"Fehler beim Laden von {file}: {e}")

    plt.xlabel("Wavelength (nm)")
    plt.ylabel("Intensity (a.u.)")
    plt.title("Alle Spektren aus TXT-Dateien")
    plt.legend(fontsize='small', loc='best')
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def average_spectra_in_folder(folder):
    # Find all txt files in the given folder (not recursive)
    txt_files = glob.glob(os.path.join(folder, "*.txt"))
    if not txt_files:
        print("No spectra found in", folder)
        return

    # Group files by prefix (before datetime, assumed as first '_' before numbers)
    from collections import defaultdict
    import re

    groups = defaultdict(list)
    for file in txt_files:
        basename = os.path.basename(file)
        # Extract prefix before first _ followed by a digit (datetime)
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
            try:
                data = np.loadtxt(file, comments='#', delimiter=None)
                if data.ndim < 2 or data.shape[1] < 2:
                    continue
                x = data[:, 0]
                y = data[:, 1]
                if x_ref is None:
                    x_ref = x
                elif not np.allclose(x, x_ref):
                    print(f"Skipping {file}: x-axis mismatch.")
                    continue
                spectra.append(y)
            except Exception as e:
                print(f"Fehler beim Laden von {file}: {e}")
        if spectra and x_ref is not None:
            y_avg = np.mean(spectra, axis=0)
            avg_data = np.column_stack((x_ref, y_avg))
            avg_filename = os.path.join(folder, f"{prefix}_average.txt")
            np.savetxt(avg_filename, avg_data, fmt="%.6f", header="Wavelength\tAverage Intensity")
            print(f"Averaged file saved: {avg_filename}")


def reference_averaged_spectra_to_dmso(folder, dmso_prefix="pure_DMSO_spectrum"):
    """
    For all averaged spectra in the folder, subtract the DMSO reference and save as new files.
    The DMSO reference is identified by its prefix (default: 'pure_DMSO_spectrum_average.txt').
    Output files are named <prefix>_average_referenced_to_DMSO.txt.
    """

    # Find all *_average.txt files
    avg_files = glob.glob(os.path.join(folder, "*_average.txt"))
    # Identify DMSO reference file
    dmso_file = None
    for f in avg_files:
        if os.path.basename(f).startswith(dmso_prefix):
            dmso_file = f
            break
    if not dmso_file:
        print(f"DMSO reference file with prefix '{dmso_prefix}' not found.")
        return

    # Load DMSO reference
    dmso_data = np.loadtxt(dmso_file)
    x_dmso = dmso_data[:, 0]
    y_dmso = dmso_data[:, 1]

    for avg_file in avg_files:
        if avg_file == dmso_file:
            continue
        try:
            data = np.loadtxt(avg_file)
            x = data[:, 0]
            y = data[:, 1]
            if not np.allclose(x, x_dmso):
                print(f"Skipping {avg_file}: x-axis mismatch with DMSO reference.")
                continue
            y_diff = y - y_dmso
            diff_data = np.column_stack((x, y_diff))
            out_name = os.path.splitext(avg_file)[0] + "_referenced_to_DMSO.txt"
            np.savetxt(out_name, diff_data, fmt="%.6f", header="Wavelength\tIntensity diff (sample - DMSO)")
            print(f"Referenced file saved: {out_name}")
        except Exception as e:
            print(f"Fehler beim Referenzieren von {avg_file}: {e}")


def calculate_and_plot_absorbance(folder, ref_filename="pure_DMSO_spectrum_average.txt"):
    """
    Calculates and plots absorbance spectra for all averaged sample spectra in the folder,
    using the given reference spectrum.
    """
    # Load reference spectrum
    ref_path = os.path.join(folder, ref_filename)
    if not os.path.exists(ref_path):
        print(f"Reference file '{ref_path}' not found.")
        return

    ref_data = np.loadtxt(ref_path)
    wavelengths = ref_data[:, 0]
    I0 = ref_data[:, 1]
    I0[I0 <= 0] = 1e-6  # Avoid division by zero

    # Find all other *_average.txt files (excluding the reference)
    sample_files = [
        f for f in glob.glob(os.path.join(folder, "*_average.txt"))
        if os.path.basename(f) != ref_filename
    ]

    plt.figure(figsize=(10, 6))

    for sample_file in sample_files:
        try:
            sample_data = np.loadtxt(sample_file)
            I = sample_data[:, 1]
            I[I <= 0] = 1e-6  # Avoid division by zero

            # Check wavelength alignment
            if not np.allclose(sample_data[:, 0], wavelengths):
                print(f"Skipping {sample_file}: wavelength axis mismatch.")
                continue

            absorbance = np.log10(I0 / I)
            plt.plot(wavelengths, absorbance, label=os.path.basename(sample_file))

            # Save absorbance spectrum
            out_name = os.path.splitext(sample_file)[0] + "_absorbance.txt"
            np.savetxt(
                out_name,
                np.column_stack((wavelengths, absorbance)),
                fmt="%.6f",
                header="Wavelength\tAbsorbance"
            )
            print(f"Absorbance spectrum saved: {out_name}")

        except Exception as e:
            print(f"Error processing {sample_file}: {e}")

    plt.xlabel("Wavelength (nm)")
    plt.ylabel("Absorbance (A)")
    plt.title("Absorbance Spectra (referenced to DMSO)")
    plt.legend(fontsize='small', loc='best')
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def calculate_and_plot_absorbance_for_all_spectra(
    sample_folder,
    ref_folder,
    ref_filename="pure_DMSO_spectrum_average.txt"
):
    """
    Calculates and plots absorbance spectra for all spectra in sample_folder,
    using the reference spectrum from ref_folder.
    """
   

    # Load reference spectrum from ref_folder
    ref_path = os.path.join(ref_folder, ref_filename)
    if not os.path.exists(ref_path):
        print(f"Reference file '{ref_path}' not found.")
        return

    ref_data = np.loadtxt(ref_path)
    wavelengths = ref_data[:, 0]
    I0 = ref_data[:, 1]
    I0[I0 <= 0] = 1e-6  # Avoid division by zero

    # Find all .txt files in sample_folder (not just *_average.txt)
    sample_files = [
        f for f in glob.glob(os.path.join(sample_folder, "*.txt"))
        if os.path.isfile(f)
    ]

    plt.figure(figsize=(10, 6))

    for sample_file in sample_files:
        try:
            sample_data = np.loadtxt(sample_file)
            if sample_data.ndim < 2 or sample_data.shape[1] < 2:
                print(f"Skipping {sample_file}: not enough columns.")
                continue
            x = sample_data[:, 0]
            I = sample_data[:, 1]
            I[I <= 0] = 1e-6  # Avoid division by zero

            # Check wavelength alignment
            if not np.allclose(x, wavelengths):
                print(f"Skipping {sample_file}: wavelength axis mismatch.")
                continue

            absorbance = np.log10(I0 / I)
            plt.plot(x, absorbance, label=os.path.basename(sample_file))

            # Save absorbance spectrum
            out_name = os.path.splitext(sample_file)[0] + "_absorbance.txt"
            np.savetxt(
                out_name,
                np.column_stack((x, absorbance)),
                fmt="%.6f",
                header="Wavelength\tAbsorbance"
            )
            print(f"Absorbance spectrum saved: {out_name}")

        except Exception as e:
            print(f"Error processing {sample_file}: {e}")

    plt.xlabel("Wavelength (nm)")
    plt.ylabel("Absorbance (A)")
    plt.title("Absorbance Spectra (referenced to DMSO)")
    plt.legend(fontsize='small', loc='best')
    plt.grid(True)
    plt.tight_layout()
    plt.show()





if __name__ == "__main__":
    #plot_spectra_from_Spectra_folder()
    #average_spectra_in_folder(r"C:\Users\xo37lay\source\repos\Auto_Polymerization\Auto_Polymerization\Spectra\pure_compounds_spectra_test")
    #reference_averaged_spectra_to_dmso(r"C:\Users\xo37lay\source\repos\Auto_Polymerization\Auto_Polymerization\Spectra\pure_compounds_spectra_test")
    #calculate_and_plot_absorbance(r"C:\Users\xo37lay\source\repos\Auto_Polymerization\Auto_Polymerization\Spectra\pure_compounds_spectra_test")

    # For all spectra in spectra_while_stopped, referencing DMSO in pure_compounds_spectra_test
    calculate_and_plot_absorbance_for_all_spectra(
        sample_folder=r"C:\Users\xo37lay\source\repos\Auto_Polymerization\Auto_Polymerization\Spectra\spectra_while_stopped",
        ref_folder=r"C:\Users\xo37lay\source\repos\Auto_Polymerization\Auto_Polymerization\Spectra\pure_compounds_spectra_test"
    )