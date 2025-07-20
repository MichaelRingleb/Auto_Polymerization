"""
Test script for pre-polymerization setup workflow.
Tests the t0 baseline acquisition and summary file creation without hardware.
"""
import os
import tempfile
from datetime import datetime
from src.NMR.nmr_utils import acquire_multiple_t0_measurements
from src.workflow_steps._2_polymerization_monitoring import create_monitoring_summary


def test_t0_baseline_acquisition():
    """Test t0 baseline acquisition with mock data."""
    print("Testing t0 baseline acquisition...")
    
    # Mock medusa and parameters
    class MockMedusa:
        def __init__(self):
            self.logger = MockLogger()
    
    class MockLogger:
        def info(self, msg): print(f"[INFO] {msg}")
        def warning(self, msg): print(f"[WARNING] {msg}")
        def error(self, msg): print(f"[ERROR] {msg}")
    
    medusa = MockMedusa()
    
    # Mock monitoring parameters
    monitoring_params = {
        "nmr_monomer_region": (5.0, 6.0),
        "nmr_standard_region": (6.5, 7.5),
        "nmr_noise_region": (9.0, 10.0),
        "nmr_scans": 32,
        "nmr_spectrum_center": 5,
        "nmr_spectrum_width": 12,
        "measurement_interval_minutes": 10,
        "shimming_interval": 4,
        "conversion_threshold": 80,
        "max_monitoring_hours": 20
    }
    
    experiment_id = "TEST_001"
    
    # Create temporary directory for test data
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temporary directory: {temp_dir}")
        
        # Test t0 baseline acquisition (this will fail without hardware, but we can test the logic)
        try:
            t0_result = acquire_multiple_t0_measurements(
                medusa, monitoring_params, experiment_id, num_measurements=3, nmr_data_base_path=temp_dir
            )
            
            print(f"T0 result success: {t0_result['success']}")
            if t0_result['success']:
                print(f"Successful measurements: {t0_result['successful_count']}/{t0_result['total_count']}")
                print(f"Average monomer area: {t0_result['average_monomer_area']:.2f}")
                print(f"Average standard area: {t0_result['average_standard_area']:.2f}")
                print(f"Average ratio: {t0_result['average_ratio']:.4f}")
            else:
                print(f"T0 acquisition failed: {t0_result.get('error_message', 'Unknown error')}")
                
        except Exception as e:
            print(f"T0 acquisition test failed (expected without hardware): {str(e)}")
        
        # Test summary file creation with mock data
        print("\nTesting summary file creation...")
        
        # Mock t0 baseline data
        mock_t0_baseline = {
            'success': True,
            'successful_count': 2,
            'total_count': 3,
            'average_monomer_area': 150.5,
            'average_standard_area': 100.2,
            'average_ratio': 1.502,
            'individual_measurements': [
                {
                    'success': True,
                    'monomer_area': 150.0,
                    'standard_area': 100.0,
                    'monomer_standard_ratio': 1.500
                },
                {
                    'success': True,
                    'monomer_area': 151.0,
                    'standard_area': 100.4,
                    'monomer_standard_ratio': 1.504
                },
                {
                    'success': False,
                    'error_message': 'Hardware communication error'
                }
            ]
        }
        
        # Mock monitoring results
        mock_monitoring_results = [
            {
                'success': True,
                'timestamp': '2025-01-15 10:00:00',
                'monomer_area': 140.0,
                'standard_area': 100.0,
                'monomer_standard_ratio': 1.400,
                'conversion': 6.8
            },
            {
                'success': True,
                'timestamp': '2025-01-15 10:10:00',
                'monomer_area': 130.0,
                'standard_area': 100.0,
                'monomer_standard_ratio': 1.300,
                'conversion': 13.4
            },
            {
                'success': False,
                'timestamp': '2025-01-15 10:20:00',
                'error_message': 'NMR acquisition failed'
            },
            {
                'success': True,
                'timestamp': '2025-01-15 10:30:00',
                'monomer_area': 120.0,
                'standard_area': 100.0,
                'monomer_standard_ratio': 1.200,
                'conversion': 20.1
            }
        ]
        
        # Create summary file
        summary_path = create_monitoring_summary(
            experiment_id, mock_t0_baseline, mock_monitoring_results, monitoring_params, temp_dir
        )
        
        print(f"Summary file created: {summary_path}")
        
        # Verify summary file exists and has content
        if os.path.exists(summary_path):
            with open(summary_path, 'r') as f:
                content = f.read()
                print(f"Summary file size: {len(content)} characters")
                print("Summary file content preview:")
                print("-" * 40)
                print(content[:500] + "..." if len(content) > 500 else content)
                print("-" * 40)
        else:
            print("ERROR: Summary file was not created")
        
        # Test with failed t0 baseline
        print("\nTesting summary creation with failed t0 baseline...")
        failed_t0_baseline = {
            'success': False,
            'error_message': 'All t0 measurements failed'
        }
        
        summary_path_failed = create_monitoring_summary(
            experiment_id, failed_t0_baseline, mock_monitoring_results, monitoring_params, temp_dir
        )
        
        print(f"Summary file with failed t0: {summary_path_failed}")
        
        if os.path.exists(summary_path_failed):
            print("Summary file created successfully even with failed t0 baseline")
        else:
            print("ERROR: Summary file was not created for failed t0 case")


def test_config_parameters():
    """Test that all required config parameters are present."""
    print("\nTesting config parameters...")
    
    try:
        from users.config.platform_config import (
            polymerization_params, polymerization_monitoring_params, experiment_id, nmr_data_base_path
        )
        
        print("✓ All config imports successful")
        
        # Check polymerization parameters
        required_poly_params = [
            "solvent_volume", "monomer_volume", "cta_volume", "initiator_volume",
            "polymerization_temp", "set_rpm", "deoxygenation_time"
        ]
        
        missing_poly = [param for param in required_poly_params if param not in polymerization_params]
        if missing_poly:
            print(f"✗ Missing polymerization parameters: {missing_poly}")
        else:
            print("✓ All polymerization parameters present")
        
        # Check monitoring parameters
        required_monitoring_params = [
            "measurement_interval_minutes", "shimming_interval", "conversion_threshold",
            "max_monitoring_hours", "nmr_scans", "nmr_monomer_region", "nmr_standard_region", "nmr_noise_region"
        ]
        
        missing_monitoring = [param for param in required_monitoring_params if param not in polymerization_monitoring_params]
        if missing_monitoring:
            print(f"✗ Missing monitoring parameters: {missing_monitoring}")
        else:
            print("✓ All monitoring parameters present")
        
        # Check experiment ID
        if experiment_id:
            print(f"✓ Experiment ID: {experiment_id}")
        else:
            print("✗ Experiment ID not set")
        
        # Check data base path
        if nmr_data_base_path:
            print(f"✓ NMR data base path: {nmr_data_base_path}")
        else:
            print("✗ NMR data base path not set")
            
    except ImportError as e:
        print(f"✗ Config import failed: {str(e)}")
    except Exception as e:
        print(f"✗ Config test failed: {str(e)}")


def main():
    """Run all tests."""
    print("=" * 60)
    print("PRE-POLYMERIZATION SETUP WORKFLOW TEST")
    print("=" * 60)
    
    test_config_parameters()
    test_t0_baseline_acquisition()
    
    print("\n" + "=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    main() 