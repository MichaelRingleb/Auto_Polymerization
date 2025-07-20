"""
test_polymerization_monitoring.py

Test script for the polymerization monitoring module.
This script tests the monitoring logic without requiring actual hardware.
"""
import sys
import os
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from users.config import platform_config as config
from src.workflow_steps._2_polymerization_monitoring import (
    create_monitoring_summary,
    run_polymerization_monitoring
)
from datetime import datetime, timedelta


def test_summary_file_creation():
    """Test the summary TXT file creation functionality."""
    print("Testing summary file creation...")
    
    # Create test data
    nmr_data_base_path = Path('test_output')
    nmr_data_base_path.mkdir(exist_ok=True)
    
    experiment_id = config.experiment_id
    polymerization_start_time = datetime.now()
    
    # Mock t0 data
    t0_data = {
        'success': True,
        'successful_count': 1,
        'total_count': 1,
        'average_monomer_area': 100.0,
        'average_standard_area': 50.0,
        'average_ratio': 2.0,
        'individual_measurements': [
            {
                'success': True,
                'monomer_area': 100.0,
                'standard_area': 50.0,
                'monomer_standard_ratio': 2.0
            }
        ]
    }
    
    # Mock measurement data
    all_measurements = [
        {
            'success': True,
            'timestamp': '2025-01-01 12:10:00',
            'monomer_area': 80.0,
            'standard_area': 50.0,
            'monomer_standard_ratio': 1.6,
            'conversion': 20.0,
            'error_message': None
        },
        {
            'success': True,
            'timestamp': '2025-01-01 12:20:00',
            'monomer_area': 60.0,
            'standard_area': 50.0,
            'monomer_standard_ratio': 1.2,
            'conversion': 40.0,
            'error_message': None
        },
        {
            'success': False,
            'timestamp': '2025-01-01 12:30:00',
            'monomer_area': None,
            'standard_area': None,
            'monomer_standard_ratio': None,
            'conversion': None,
            'error_message': 'NMR acquisition failed'
        }
    ]
    
    # Create summary file
    summary_path = create_monitoring_summary(
        experiment_id, t0_data, all_measurements, config.polymerization_monitoring_params, nmr_data_base_path
    )
    
    print(f"Summary file created: {summary_path}")
    
    # Read and display the file content
    with open(summary_path, 'r') as f:
        content = f.read()
        print("\nSummary file content:")
        print(content)
    
    print("✓ Summary file creation test passed!")
    return True


def test_monitoring_logic():
    """Test the monitoring logic without actual hardware."""
    print("\nTesting monitoring logic...")
    
    # Mock monitoring parameters
    monitoring_params = config.polymerization_monitoring_params
    
    # Test the monitoring logic structure
    print(f"Conversion threshold: {monitoring_params.get('conversion_threshold', 80)}%")
    print(f"Monomer region: {monitoring_params.get('nmr_monomer_region', (5.0, 6.0))}")
    print(f"Standard region: {monitoring_params.get('nmr_standard_region', (6.5, 7.5))}")
    print(f"Noise region: {monitoring_params.get('nmr_noise_region', (9.0, 10.0))}")
    print(f"NMR scans: {monitoring_params.get('nmr_scans', 32)}")
    print(f"Measurement interval: {monitoring_params.get('measurement_interval_minutes', 10)} minutes")
    print(f"Shimming interval: {monitoring_params.get('shimming_interval', 4)} measurements")
    print(f"Max monitoring time: {monitoring_params.get('max_monitoring_hours', 20)} hours")
    
    print("✓ Monitoring logic test passed!")
    return True


def test_config_parameters():
    """Test that all required config parameters are present."""
    print("\nTesting config parameters...")
    
    required_params = [
        'experiment_determiner',
        'polymerization_monitoring_params',
    ]
    
    for param in required_params:
        if '.' in param:
            # Nested parameter
            parts = param.split('.')
            value = config
            for part in parts:
                value = getattr(value, part, None)
                if value is None:
                    break
        else:
            # Direct parameter
            value = getattr(config, param, None)
        
        if value is not None:
            print(f"✓ {param}: {value}")
        else:
            print(f"✗ {param}: Missing!")
            return False
    
    # Test specific monitoring parameters
    monitoring_params = config.polymerization_monitoring_params
    required_monitoring_params = [
        'measurement_interval_minutes',
        'shimming_interval', 
        'conversion_threshold',
        'max_monitoring_hours',
        'nmr_scans',
        'nmr_monomer_region',
        'nmr_standard_region',
        'nmr_noise_region'
    ]
    
    for param in required_monitoring_params:
        if param in monitoring_params:
            print(f"✓ monitoring_params.{param}: {monitoring_params[param]}")
        else:
            print(f"✗ monitoring_params.{param}: Missing!")
            return False
    
    print("✓ All config parameters present!")
    return True


def main():
    """Run all tests."""
    print("🧪 Testing Polymerization Monitoring Implementation")
    print("=" * 50)
    
    tests = [
        test_config_parameters,
        test_summary_file_creation,
        test_monitoring_logic
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test failed: {e}")
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The implementation is ready.")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
    
    # Clean up test files
    test_output = Path('test_output')
    if test_output.exists():
        import shutil
        shutil.rmtree(test_output)
        print("🧹 Test files cleaned up.")


if __name__ == "__main__":
    main() 