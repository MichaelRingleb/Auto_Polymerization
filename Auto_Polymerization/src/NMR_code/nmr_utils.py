"""
NMR Utilities for Auto_Polymerization Platform

This module provides high-level utilities for NMR spectroscopy operations
using the Nanalysis NMR spectrometer. It includes functions for:
- NMR locking and shimming
- Spectrum acquisition and processing
- Conversion analysis for polymerization monitoring
- Data management and visualization

Dependencies:
    - numpy: For numerical operations and array handling
    - matterlab_nmr: For NMR spectrometer communication
    - pathlib: For cross-platform path handling
    - logging: For robust, configurable logging
    - matplotlib: For spectrum visualization
    - scipy: For signal processing and optimization

Hardware Requirements:
    - Nanalysis NMR spectrometer (network connection)
    - Default URL: http://nmr.matterlab.sandbox:5000

Usage Example:
    # Initialize NMR connection
    nmr = initialize_nmr()
    
    # Lock and shim on deuterated solvent
    lock_and_shim_nmr(nmr, solvent_type="D2O")
    
    # Take a spectrum and analyze conversion
    spectrum_data, conversion = take_spectrum_and_analyze(nmr, sample_type="polymerization")
    
    # Save spectrum data
    save_spectrum_data(nmr, "polymerization_sample", spectrum_data)

Author: Michael Ringleb (with help from cursor.ai)
Date: [08.07.2025]
Version: 0.1
"""

import logging
import numpy as np
from pathlib import Path
from datetime import datetime
import time
from typing import Optional, Dict, Tuple, Union, List
import matplotlib.pyplot as plt
from scipy.optimize import minimize
from scipy.signal import find_peaks

# Import NMR spectrometer class
try:
    from matterlab_nmr.nanalysis_nmr_spectrometer import (
        NMR60Pro, Nuclei, DSolv, HSolv, ShimMethod, 
        NMRExperiment, SuppressionMode
    )
except ImportError:
    print("Warning: matterlab_nmr not found. NMR functions will not work.")
    NMR60Pro = None
    Nuclei = None
    DSolv = None
    HSolv = None
    ShimMethod = None
    NMRExperiment = None
    SuppressionMode = None

# Set up module-level logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Constants
DEFAULT_NMR_URL = "http://nmr.matterlab.sandbox:5000"
DATA_FOLDER = "users/data/NMR_data"
DEFAULT_NUM_SCANS = 8
DEFAULT_APODIZATION = 0.2
DEFAULT_NUM_POINTS = 2048

# Conversion analysis parameters
TARGET_PEAK_PPM = 5.5  # Target peak for conversion analysis (adjust as needed)
PEAK_TOLERANCE_PPM = 0.1  # Tolerance for peak detection
BASELINE_REGION_PPM = (8.0, 10.0)  # Region for baseline calculation

# File headers
HEADER_SPECTRUM = "Chemical_Shift_ppm\tIntensity"
HEADER_CONVERSION = "Timestamp\tConversion_Percent\tPeak_Intensity\tBaseline_Intensity"

class NMRUtils:
    """Main NMR utilities class for Auto_Polymerization platform."""
    
    def __init__(self, nmr_url: str = DEFAULT_NMR_URL, data_folder: str = DATA_FOLDER):
        """
        Initialize NMR utilities.
        
        Args:
            nmr_url: URL of the NMR spectrometer server
            data_folder: Folder to store NMR data
        """
        self.nmr_url = nmr_url
        self.data_folder = Path(data_folder)
        self.data_folder.mkdir(parents=True, exist_ok=True)
        self.nmr = None
        self._initialize_nmr()
        
    def _initialize_nmr(self):
        """Initialize NMR spectrometer connection."""
        if NMR60Pro is None:
            logger.error("NMR spectrometer module not available")
            return
            
        try:
            self.nmr = NMR60Pro(url=self.nmr_url)
            logger.info(f"NMR spectrometer connected at {self.nmr_url}")
        except Exception as e:
            logger.error(f"Failed to connect to NMR spectrometer: {e}")
            self.nmr = None
    
    def is_connected(self) -> bool:
        """Check if NMR spectrometer is connected."""
        if self.nmr is None:
            return False
        try:
            return self.nmr.connected
        except:
            return False
    
    def lock_and_shim(self, 
                     solvent_type: str = "DMSO", 
                     shim_method = None,
                     num_scans: int = DEFAULT_NUM_SCANS) -> bool:
        """
        Lock and shim NMR on deuterated solvent.
        
        Args:
            solvent_type: Type of deuterated solvent ("D2O", "CDCL3", "DMSO_D6", etc.)
            shim_method: Shimming method (QUICK, MEDIUM, FULL)
            num_scans: Number of scans for shimming
            
        Returns:
            bool: True if successful, False otherwise
        """
        if shim_method is None:
            if ShimMethod is not None:
                shim_method = ShimMethod.QUICK
            else:
                logger.error("ShimMethod enum not available.")
                return False
        if not self.is_connected():
            logger.error("NMR spectrometer not connected")
            return False
        if self.nmr is None or NMRExperiment is None:
            logger.error("NMR60Pro instance or NMRExperiment enum not available.")
            return False
        try:
            # Map solvent type to enum
            solvent_enum = self._get_solvent_enum(solvent_type)
            if solvent_enum is None:
                logger.error("Could not resolve DSolv enum for solvent_type: %s", solvent_type)
                return False
            # Set up hardlock experiment for deuterated solvent
            self.nmr.set_hardlock_exp(
                num_scans=num_scans,
                solvent=solvent_enum,  # type: ignore
                experiment=NMRExperiment.ONE_D
            )
            
            # Perform shimming
            logger.info(f"Starting shimming with method: {shim_method}")
            resolution = self.nmr.shim(method=shim_method)
            logger.info(f"Shimming complete. Resolution: {resolution}")
            
            return True
            
        except Exception as e:
            logger.error(f"Lock and shim failed: {e}")
            return False
    
    def lock_and_shim_non_deuterated(self, 
                                 solvent_type: str = "H2O", 
                                 shim_method = None,
                                 num_scans: int = DEFAULT_NUM_SCANS) -> bool:
        """
        Lock and shim NMR on non-deuterated (protonated) solvent.
        Args:
            solvent_type: Type of protonated solvent ("H2O", "DMSO", "CH3OH", etc.)
            shim_method: Shimming method (QUICK, MEDIUM, FULL)
            num_scans: Number of scans for shimming
        Returns:
            bool: True if successful, False otherwise
        """
        if shim_method is None:
            if ShimMethod is not None:
                shim_method = ShimMethod.QUICK
            else:
                logger.error("ShimMethod enum not available.")
                return False
        if not self.is_connected():
            logger.error("NMR spectrometer not connected")
            return False
        if self.nmr is None or NMRExperiment is None or Nuclei is None or HSolv is None:
            logger.error("NMR60Pro instance or required enums not available.")
            return False
        try:
            # Map solvent type to HSolv enum
            solvent_mapping = {
                'H2O': HSolv.H2O if HSolv else None,
                'DMSO': HSolv.DMSO if HSolv else None,
                'CH3OH': HSolv.CH3OH if HSolv else None,
                'C6H6': HSolv.C6H6 if HSolv else None,
                'CHCL3': HSolv.CHCL3 if HSolv else None,
                'GENERIC_1_P': HSolv.GENERIC_1_P if HSolv else None,
                'GENERIC_2_P': HSolv.GENERIC_2_P if HSolv else None,
                'GENERIC_3_P': HSolv.GENERIC_3_P if HSolv else None,
                'DIOXANE': HSolv.DIOXANE if HSolv else None,
            }
            solvent_enum = solvent_mapping.get(solvent_type.upper(), None)
            if solvent_enum is None:
                logger.error("Could not resolve HSolv enum for solvent_type: %s", solvent_type)
                return False
            # Set up regular experiment for protonated solvent
            self.nmr.set_regular_exp(
                num_scans=num_scans,
                nuclei=Nuclei.PROTON,
                solvent=solvent_enum,  # type: ignore
                experiment=NMRExperiment.ONE_D
            )

            # Perform shimming
            logger.info(f"Starting shimming with method: {shim_method} (non-deuterated)")
            resolution = self.nmr.shim(method=shim_method)
            logger.info(f"Shimming complete. Resolution: {resolution}")

            return True

        except Exception as e:
            logger.error(f"Lock and shim (non-deuterated) failed: {e}")
            return False
    
    def take_spectrum(self, 
                     sample_type: str = "polymerization",
                     nuclei = None,
                     solvent = None,
                     num_scans: int = DEFAULT_NUM_SCANS,
                     spectrum_center: float = None,
                     spectrum_width: float = None,
                     auto_phase: bool = True) -> Optional[Dict]:
        """
        Take NMR spectrum of sample.
        
        Args:
            sample_type: Type of sample for naming
            nuclei: Nucleus to observe
            solvent: Solvent type
            num_scans: Number of scans
            spectrum_center: Spectrum center in ppm
            spectrum_width: Spectrum width in ppm
            auto_phase: Whether to apply auto-phasing
            
        Returns:
            Dict containing spectrum data or None if failed
        """
        if not self.is_connected():
            logger.error("NMR spectrometer not connected")
            return None
        if self.nmr is None or NMRExperiment is None or Nuclei is None or DSolv is None:
            logger.error("NMR60Pro instance or required enums not available.")
            return None
        if nuclei is None:
            if Nuclei is not None:
                nuclei = Nuclei.PROTON
            else:
                logger.error("Nuclei enum not available.")
                return None
        if solvent is None:
            if DSolv is not None:
                solvent = DSolv.CDCL3
            else:
                logger.error("DSolv enum not available.")
                return None
        try:
            # Set up experiment
            if nuclei is None:
                if Nuclei is not None:
                    nuclei = Nuclei.PROTON
                else:
                    logger.error("Nuclei enum not available.")
                    return None
            if solvent is None:
                if DSolv is not None:
                    solvent = DSolv.CDCL3
                else:
                    logger.error("DSolv enum not available.")
                    return None
            # Ensure nuclei and solvent are correct types
            if isinstance(nuclei, float) or nuclei is None:
                logger.error("Invalid nuclei value for set_regular_exp.")
                return None
            if isinstance(solvent, float) or solvent is None:
                logger.error("Invalid solvent value for set_regular_exp.")
                return None
            exp_kwargs = dict(
                num_scans=int(num_scans),
                nuclei=nuclei,
                solvent=solvent,
                experiment=NMRExperiment.ONE_D,
                apodization=float(DEFAULT_APODIZATION),
                num_points=int(DEFAULT_NUM_POINTS)
            )
            if spectrum_center is not None and isinstance(spectrum_center, (float, int)):
                exp_kwargs['spectrum_center'] = float(spectrum_center)
            if spectrum_width is not None and isinstance(spectrum_width, (float, int)):
                exp_kwargs['spectrum_width'] = float(spectrum_width)
            self.nmr.set_regular_exp(**exp_kwargs)
            
            # Run experiment
            logger.info(f"Starting NMR experiment for {sample_type}")
            self.nmr.run()
            
            # Process spectrum
            self.nmr.proc_1D(auto_phase=auto_phase)
            
            # Prepare data dictionary
            spectrum_data = {
                'frequencies_ppm': self.nmr._freqs_ppm,
                'spectrum': self.nmr._spec,
                'raw_data': self.nmr.raw_data,
                'metadata': self.nmr._meta_data,
                'sample_type': sample_type,
                'timestamp': datetime.now(),
                'nuclei': nuclei,
                'solvent': solvent,
                'num_scans': num_scans
            }
            
            logger.info(f"NMR spectrum acquired for {sample_type}")
            return spectrum_data
            
        except Exception as e:
            logger.error(f"Failed to take NMR spectrum: {e}")
            return None
    
    def analyze_conversion(self, 
                          spectrum_data: Dict,
                          target_peak_ppm: float = TARGET_PEAK_PPM,
                          peak_tolerance: float = PEAK_TOLERANCE_PPM,
                          baseline_region: Tuple[float, float] = BASELINE_REGION_PPM) -> Dict:
        """
        Analyze polymerization conversion from NMR spectrum.
        
        Args:
            spectrum_data: Spectrum data from take_spectrum()
            target_peak_ppm: Target peak position in ppm
            peak_tolerance: Tolerance for peak detection
            baseline_region: Region for baseline calculation
            
        Returns:
            Dict containing conversion analysis results
        """
        try:
            freqs_ppm = spectrum_data['frequencies_ppm']
            spectrum = np.real(spectrum_data['spectrum'])
            
            # Find target peak
            peak_mask = (freqs_ppm >= target_peak_ppm - peak_tolerance) & \
                       (freqs_ppm <= target_peak_ppm + peak_tolerance)
            
            if not np.any(peak_mask):
                logger.warning(f"No peak found near {target_peak_ppm} ppm")
                return {'conversion': 0.0, 'peak_intensity': 0.0, 'baseline_intensity': 0.0}
            
            peak_intensity = np.max(spectrum[peak_mask])
            peak_position = freqs_ppm[peak_mask][np.argmax(spectrum[peak_mask])]
            
            # Calculate baseline
            baseline_mask = (freqs_ppm >= baseline_region[0]) & (freqs_ppm <= baseline_region[1])
            baseline_intensity = np.mean(spectrum[baseline_mask]) if np.any(baseline_mask) else 0.0
            
            # Calculate conversion (normalized to baseline)
            if baseline_intensity > 0:
                conversion = (peak_intensity / baseline_intensity) * 100
            else:
                conversion = 0.0
            
            analysis_result = {
                'conversion': conversion,
                'peak_intensity': peak_intensity,
                'baseline_intensity': baseline_intensity,
                'peak_position': peak_position,
                'target_peak_ppm': target_peak_ppm,
                'timestamp': datetime.now()
            }
            
            logger.info(f"Conversion analysis: {conversion:.1f}% at {peak_position:.2f} ppm")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Failed to analyze conversion: {e}")
            return {'conversion': 0.0, 'peak_intensity': 0.0, 'baseline_intensity': 0.0}
    
    def take_spectrum_and_analyze(self, 
                                 sample_type: str = "polymerization",
                                 target_peak_ppm: float = TARGET_PEAK_PPM,
                                 **spectrum_kwargs) -> Tuple[Optional[Dict], float]:
        """
        Take NMR spectrum and analyze conversion in one step.
        
        Args:
            sample_type: Type of sample
            target_peak_ppm: Target peak for conversion analysis
            **spectrum_kwargs: Additional arguments for take_spectrum()
            
        Returns:
            Tuple of (spectrum_data, conversion_percent)
        """
        spectrum_data = self.take_spectrum(sample_type=sample_type, **spectrum_kwargs)
        
        if spectrum_data is None:
            return None, 0.0
        
        analysis_result = self.analyze_conversion(spectrum_data, target_peak_ppm=target_peak_ppm)
        conversion = analysis_result['conversion']
        
        return spectrum_data, conversion
    
    def save_spectrum_data(self, 
                          spectrum_data: Dict, 
                          base_name: str,
                          save_plot: bool = True) -> bool:
        """
        Save NMR spectrum data to files.
        
        Args:
            spectrum_data: Spectrum data from take_spectrum()
            base_name: Base name for saved files
            save_plot: Whether to save spectrum plot
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            timestamp = spectrum_data['timestamp'].strftime("%Y-%m-%d_%H-%M-%S")
            filename_base = f"{base_name}_{timestamp}"
            
            # Save spectrum data
            spectrum_file = self.data_folder / f"{filename_base}_spectrum.txt"
            freqs_ppm = spectrum_data['frequencies_ppm']
            spectrum = np.real(spectrum_data['spectrum'])
            
            with open(spectrum_file, 'w') as f:
                f.write(f"# {HEADER_SPECTRUM}\n")
                f.write(f"# Sample: {spectrum_data['sample_type']}\n")
                f.write(f"# Timestamp: {spectrum_data['timestamp']}\n")
                f.write(f"# Nuclei: {spectrum_data['nuclei']}\n")
                f.write(f"# Solvent: {spectrum_data['solvent']}\n")
                f.write(f"# Scans: {spectrum_data['num_scans']}\n")
                for freq, intensity in zip(freqs_ppm, spectrum):
                    f.write(f"{freq:.4f}\t{intensity:.6f}\n")
            
            # Save raw data if available
            if spectrum_data.get('raw_data'):
                raw_file = self.data_folder / f"{filename_base}_raw.dx"
                with open(raw_file, 'w') as f:
                    f.write(spectrum_data['raw_data'])
            
            # Save plot if requested
            if save_plot:
                self._save_spectrum_plot(spectrum_data, filename_base)
            
            logger.info(f"Spectrum data saved: {filename_base}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save spectrum data: {e}")
            return False
    
    def _save_spectrum_plot(self, spectrum_data: Dict, filename_base: str):
        """Save spectrum plot."""
        try:
            freqs_ppm = spectrum_data['frequencies_ppm']
            spectrum = np.real(spectrum_data['spectrum'])
            
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(freqs_ppm, spectrum, 'b-', linewidth=0.8)
            ax.invert_xaxis()
            ax.set_xlabel('Chemical Shift (ppm)')
            ax.set_ylabel('Intensity')
            ax.set_title(f"NMR Spectrum - {spectrum_data['sample_type']}")
            ax.grid(True, alpha=0.3)
            # No target_peak_ppm attribute, so skip vertical line
            plt.tight_layout()
            
            plot_file = self.data_folder / f"{filename_base}_plot.png"
            plt.savefig(plot_file, dpi=300, bbox_inches='tight')
            plt.close()
            
        except Exception as e:
            logger.error(f"Failed to save spectrum plot: {e}")
    
    def _get_solvent_enum(self, solvent_type: str):
        """Map solvent string to appropriate enum, with runtime check for DSolv."""
        if DSolv is None:
            logger.error("DSolv enum not available.")
            return None
        solvent_mapping = {
            'D2O': DSolv.H2O if hasattr(DSolv, 'H2O') else None,
            'CDCL3': DSolv.CDCL3 if hasattr(DSolv, 'CDCL3') else None,
            'DMSO_D6': DSolv.DMSO_D6 if hasattr(DSolv, 'DMSO_D6') else None,
            'CD3OD': DSolv.CD3OD if hasattr(DSolv, 'CD3OD') else None,
            'ACETONE_D6': DSolv.ACETONE_D6 if hasattr(DSolv, 'ACETONE_D6') else None,
            'C6D6': DSolv.C6D6 if hasattr(DSolv, 'C6D6') else None,
            'TFA_D': DSolv.TFA_D if hasattr(DSolv, 'TFA_D') else None,
            'C2D5OD': DSolv.C2D5OD if hasattr(DSolv, 'C2D5OD') else None,
            'C7D8': DSolv.C7D8 if hasattr(DSolv, 'C7D8') else None,
            'THF_D8': DSolv.THF_D8 if hasattr(DSolv, 'THF_D8') else None,
            'CD3CN': DSolv.CD3CN if hasattr(DSolv, 'CD3CN') else None,
            'CD2CL2': DSolv.CD2CL2 if hasattr(DSolv, 'CD2CL2') else None,
        }
        enum_val = solvent_mapping.get(solvent_type.upper(), None)
        if enum_val is None:
            logger.error("Could not resolve DSolv enum for solvent_type: %s", solvent_type)
        return enum_val
    
    def get_spectrometer_status(self) -> Dict:
        """Get comprehensive spectrometer status."""
        if not self.is_connected():
            return {'connected': False}
        
        try:
            return {
                'connected': self.nmr.connected,
                'serial_number': self.nmr.serial_number,
                'software_version': self.nmr.software_version,
                'spectrometer_freq': self.nmr.spectrometer_freq,
                'standby_mode': self.nmr.standby_mode,
                'resolution': self.nmr.resolution,
                'temperature_sensors': self.nmr.temperature_sensors,
                'rpc_enabled': self.nmr.rpc_enabled
            }
        except Exception as e:
            logger.error(f"Failed to get spectrometer status: {e}")
            return {'connected': False, 'error': str(e)}


# Convenience functions for backward compatibility
def initialize_nmr(nmr_url: str = DEFAULT_NMR_URL) -> NMRUtils:
    """Initialize NMR utilities."""
    return NMRUtils(nmr_url=nmr_url)

def lock_and_shim_nmr(nmr_utils: 'NMRUtils', 
                     solvent_type: str = "D2O", 
                     shim_method = None) -> bool:
    """Lock and shim NMR on deuterated solvent."""
    return nmr_utils.lock_and_shim(solvent_type=solvent_type, shim_method=shim_method)

def lock_and_shim_nmr_non_deuterated(nmr_utils: 'NMRUtils', 
                                     solvent_type: str = "H2O", 
                                     shim_method = None) -> bool:
    """Lock and shim NMR on non-deuterated (protonated) solvent."""
    return nmr_utils.lock_and_shim_non_deuterated(solvent_type=solvent_type, shim_method=shim_method)

def take_spectrum_and_analyze(nmr_utils: NMRUtils, 
                             sample_type: str = "polymerization",
                             target_peak_ppm: float = TARGET_PEAK_PPM,
                             **kwargs) -> Tuple[Optional[Dict], float]:
    """Take NMR spectrum and analyze conversion."""
    return nmr_utils.take_spectrum_and_analyze(
        sample_type=sample_type, 
        target_peak_ppm=target_peak_ppm, 
        **kwargs
    )

def save_spectrum_data(nmr_utils: NMRUtils, 
                      spectrum_data: Dict, 
                      base_name: str) -> bool:
    """Save NMR spectrum data."""
    return nmr_utils.save_spectrum_data(spectrum_data, base_name) 