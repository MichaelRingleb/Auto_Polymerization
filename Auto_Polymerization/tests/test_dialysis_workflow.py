import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
import tempfile
import shutil
from datetime import datetime
from workflow_steps._3_dialysis_module import run_dialysis_workflow

class MockLogger:
    def info(self, msg): print(f"[INFO] {msg}")
    def warning(self, msg): print(f"[WARNING] {msg}")
    def error(self, msg): print(f"[ERROR] {msg}")

class MockMedusa:
    def __init__(self):
        self.logger = MockLogger()
        self.log_info = self.logger.info
        self.log_warn = self.logger.warning
        self.log_error = self.logger.error
        self.transfer_continuous_calls = []
        self.transfer_volumetric_calls = []
        self.write_serial_calls = []
        self.nmr_counter = 0
    def transfer_continuous(self, **kwargs):
        self.transfer_continuous_calls.append(kwargs)
        self.logger.info(f"Mock transfer_continuous: {kwargs}")
    def transfer_volumetric(self, **kwargs):
        self.transfer_volumetric_calls.append(kwargs)
        self.logger.info(f"Mock transfer_volumetric: {kwargs}")
    def write_serial(self, *args, **kwargs):
        self.write_serial_calls.append((args, kwargs))
        self.logger.info(f"Mock write_serial: {args}, {kwargs}")

# Patch NMR and shimming helpers to simulate success/failure
import src.NMR.nmr_utils as nmr_utils
import src.liquid_transfers.liquid_transfers_utils as lt_utils

def mock_acquire_and_analyze_nmr_spectrum(*args, **kwargs):
    # Simulate a successful NMR acquisition, with monomer peak decreasing each call
    mock_acquire_and_analyze_nmr_spectrum.counter += 1
    return {
        'acquisition_success': True,
        'success': True,
        'monomer_area': 1.0 / mock_acquire_and_analyze_nmr_spectrum.counter,
        'noise_level': 0.05,
        'ratio': 1.0 / mock_acquire_and_analyze_nmr_spectrum.counter / 0.05,
        'below_3x_noise': mock_acquire_and_analyze_nmr_spectrum.counter > 1,
        'filename': f"mockfile_{mock_acquire_and_analyze_nmr_spectrum.counter}",
        'timestamp': datetime.now().strftime('%Y-%m-%d_%H-%M-%S'),
        'iteration_counter': mock_acquire_and_analyze_nmr_spectrum.counter,
        'experiment_id': 'MOCK_EXP',
    }
mock_acquire_and_analyze_nmr_spectrum.counter = 0

def mock_perform_nmr_shimming_with_retry(*args, **kwargs):
    # Simulate shimming always succeeds
    return {'success': True, 'error_message': None}

def mock_monomer_removal_dialysis(*args, **kwargs):
    # Simulate monomer peak below threshold after 2nd iteration
    # Use the filename from kwargs if available, otherwise default
    current_filename = None
    if 'nmr_data_folder' in kwargs and 'filename' in kwargs:
        current_filename = kwargs['filename']
    # For the test, just use the expected pattern
    count = mock_acquire_and_analyze_nmr_spectrum.counter
    results = []
    for i in range(1, count + 1):
        results.append({
            'Filename': f"MOCK_EXP_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_dialysis_{i}_t0",  # Simulate matching filename
            'Peak_Height': 0.1 / i,
            'Noise_Level': 0.05,
            'Height/Noise_Ratio': 2.0 / i,
            'Above_2x_Noise': i < 2  # Below threshold after 2nd iteration
        })
    return results

# Patch the helpers
nmr_utils.acquire_and_analyze_nmr_spectrum = mock_acquire_and_analyze_nmr_spectrum
nmr_utils.perform_nmr_shimming_with_retry = mock_perform_nmr_shimming_with_retry
nmr_utils.monomer_removal_dialysis = mock_monomer_removal_dialysis
lt_utils.to_nmr_liquid_transfer_sampling = lambda medusa: medusa.logger.info("Mock to_nmr_liquid_transfer_sampling")
lt_utils.from_nmr_liquid_transfer_sampling = lambda medusa: medusa.logger.info("Mock from_nmr_liquid_transfer_sampling")


def test_dialysis_workflow():
    # Use a temp directory for summary files
    temp_dir = tempfile.mkdtemp()
    try:
        # Patch config paths
        import users.config.platform_config as config
        config.data_base_path = temp_dir
        config.nmr_data_base_path = temp_dir
        config.dialysis_params["dialysis_duration_mins"] = 1  # Short run
        config.dialysis_params["dialysis_measurement_interval_minutes"] = 0.01  # ~0.6s
        # Run the workflow
        medusa = MockMedusa()
        result = run_dialysis_workflow(medusa)
        print("\n=== Test Results ===")
        print(f"Success: {result['success']}")
        print(f"Summary TXT: {result['summary_txt']}")
        print(f"Summary CSV: {result['summary_csv']}")
        print(f"NMR Results: {result['nmr_results']}")
        print(f"Error Log: {result['error_log']}")
        # Check that summary files exist
        assert os.path.exists(result['summary_txt']), "Summary TXT file not created!"
        assert os.path.exists(result['summary_csv']), "Summary CSV file not created!"
        print("Test passed: Summary files created.")
    finally:
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    test_dialysis_workflow() 