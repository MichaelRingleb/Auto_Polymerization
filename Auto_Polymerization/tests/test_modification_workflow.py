"""
Unit test for the modification workflow module.

This test provides a minimal validation of the modification workflow functionality
using mock objects and patched dependencies.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
from pathlib import Path

# Import the modification workflow module
from src.workflow_steps._4_modification_module import (
    run_modification_workflow,
    setup_uv_vis_reference,
    setup_uv_vis_t0,
    add_modification_reagent,
    monitor_modification_reaction,
    generate_modification_summary
)
from src.liquid_transfers.liquid_transfers_utils import deoxygenate_reaction_mixture


class TestModificationWorkflow(unittest.TestCase):
    """Test cases for the modification workflow module."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a mock Medusa object
        self.mock_medusa = Mock()
        self.mock_medusa.logger = Mock()
        self.mock_medusa.write_serial = Mock()
        self.mock_medusa.transfer_volumetric = Mock()
        
        # Create a temporary directory for test data
        self.temp_dir = tempfile.mkdtemp()
        self.test_data_path = Path(self.temp_dir) / "test_data"
        self.test_data_path.mkdir()
        
        # Mock configuration
        self.mock_config = {
            "modification_volume": 2,
            "modification_draw_speed": 0.08,
            "modification_dispense_speed": 0.13,
            "modification_flush": 1,
            "modification_flush_volume": 5,
            "modification_flush_speed": 0.15,
            "deoxygenation_time_sec": 10,  # Short for testing
            "monitoring_interval_minutes": 1,  # Short for testing
            "max_monitoring_iterations": 3,  # Small for testing
            "post_modification_dialysis_hours": 1,  # Short for testing
            "uv_vis_stability_tolerance_percent": 1.0,
            "uv_vis_stability_measurements": 3,
        }
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('src.liquid_transfers.liquid_transfers_utils.time.sleep')
    def test_deoxygenate_reaction_mixture(self, mock_sleep):
        """Test deoxygenation functionality."""
        result = deoxygenate_reaction_mixture(self.mock_medusa, 5, pump_id="Solvent_Monomer_Modification_Pump")
        
        self.assertTrue(result)
        self.mock_medusa.write_serial.assert_any_call("COM12", "GAS_ON")
        self.mock_medusa.write_serial.assert_any_call("COM12", "GAS_OFF")
        self.mock_medusa.transfer_volumetric.assert_called()
    
    @patch('src.workflow_steps._4_modification_module.uv_vis.take_spectrum')
    def test_setup_uv_vis_reference(self, mock_take_spectrum):
        """Test UV-VIS reference setup."""
        # Mock successful spectrum acquisition
        mock_take_spectrum.return_value = (Mock(), Mock(), "test_reference.txt", None, False)
        
        success, filename = setup_uv_vis_reference(self.mock_medusa)
        
        self.assertTrue(success)
        self.assertEqual(filename, "test_reference.txt")
        # Note: transfer_volumetric is now called through the liquid_transfers_utils wrapper for reference transfer
    
    @patch('src.workflow_steps._4_modification_module.uv_vis.take_spectrum')
    def test_setup_uv_vis_t0(self, mock_take_spectrum):
        """Test UV-VIS t0 setup."""
        # Mock successful spectrum acquisition
        mock_take_spectrum.return_value = (Mock(), Mock(), "test_t0.txt", None, False)
        
        success, filename = setup_uv_vis_t0(self.mock_medusa)
        
        self.assertTrue(success)
        self.assertEqual(filename, "test_t0.txt")
        # Note: transfer_volumetric is now called through the liquid_transfers_utils wrapper for sampling transfer
    
    def test_add_modification_reagent(self):
        """Test modification reagent addition."""
        result = add_modification_reagent(self.mock_medusa, self.mock_config)
        
        self.assertTrue(result)
        self.mock_medusa.transfer_volumetric.assert_called_once()
    
    @patch('src.workflow_steps._4_modification_module.uv_vis.take_spectrum')
    @patch('src.workflow_steps._4_modification_module.time.sleep')
    def test_monitor_modification_reaction(self, mock_sleep, mock_take_spectrum):
        """Test modification reaction monitoring."""
        # Mock successful spectrum acquisition with reaction completion
        mock_take_spectrum.return_value = (Mock(), Mock(), "test_spectrum.txt", 85.5, True)
        
        result = monitor_modification_reaction(self.mock_medusa, self.mock_config)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['final_conversion'], 85.5)
        self.assertTrue(result['reaction_complete'])
        self.assertGreater(result['total_iterations'], 0)
    
    # Post-modification dialysis test removed - now handled in platform controller
    
    def test_generate_modification_summary(self):
        """Test summary file generation."""
        monitoring_results = {
            'total_iterations': 5,
            'final_conversion': 85.5,
            'reaction_complete': True,
            'measurements': [
                {
                    'iteration': 1,
                    'filename': 'test1.txt',
                    'conversion': 50.0,
                    'timestamp': '2025-01-01T10:00:00'
                },
                {
                    'iteration': 2,
                    'filename': 'test2.txt',
                    'conversion': 75.0,
                    'timestamp': '2025-01-01T10:01:00'
                }
            ]
        }
        
        summary_files = generate_modification_summary(
            "TEST_EXP",
            str(self.test_data_path),
            monitoring_results,
            self.mock_config
        )
        
        self.assertIsNotNone(summary_files['summary_txt'])
        self.assertIsNotNone(summary_files['summary_csv'])
        
        # Check that files were actually created
        self.assertTrue(Path(summary_files['summary_txt']).exists())
        self.assertTrue(Path(summary_files['summary_csv']).exists())
    
    @patch('src.liquid_transfers.liquid_transfers_utils.deoxygenate_reaction_mixture')
    @patch('src.workflow_steps._4_modification_module.setup_uv_vis_reference')
    @patch('src.workflow_steps._4_modification_module.setup_uv_vis_t0')
    @patch('src.workflow_steps._4_modification_module.add_modification_reagent')
    @patch('src.workflow_steps._4_modification_module.monitor_modification_reaction')
    @patch('src.workflow_steps._4_modification_module.generate_modification_summary')
    def test_run_modification_workflow_success(self, mock_generate_summary, 
                                             mock_monitor, mock_add_reagent, mock_t0, 
                                             mock_ref, mock_deoxygenate):
        """Test successful modification workflow execution."""
        # Mock all workflow steps to succeed
        mock_deoxygenate.return_value = True
        mock_ref.return_value = (True, "ref.txt")
        mock_t0.return_value = (True, "t0.txt")
        mock_add_reagent.return_value = True
        mock_monitor.return_value = {
            'success': True,
            'total_iterations': 3,
            'final_conversion': 85.5,
            'reaction_complete': True,
            'measurements': []
        }
        # Post-modification dialysis is now handled in platform controller
        mock_generate_summary.return_value = {
            'summary_txt': str(self.test_data_path / 'summary.txt'),
            'summary_csv': str(self.test_data_path / 'summary.csv')
        }
        
        result = run_modification_workflow(
            self.mock_medusa,
            self.mock_config,
            "TEST_EXP",
            str(self.test_data_path),
            str(self.test_data_path)
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['final_conversion'], 85.5)
        self.assertEqual(result['total_iterations'], 3)
        self.assertIsNotNone(result['summary_files'])
    
    @patch('src.liquid_transfers.liquid_transfers_utils.deoxygenate_reaction_mixture')
    def test_run_modification_workflow_failure(self, mock_deoxygenate):
        """Test modification workflow failure handling."""
        # Mock deoxygenation to fail
        mock_deoxygenate.return_value = False
        
        result = run_modification_workflow(
            self.mock_medusa,
            self.mock_config,
            "TEST_EXP",
            str(self.test_data_path),
            str(self.test_data_path)
        )
        
        self.assertFalse(result['success'])
        self.assertIsNotNone(result['error_message'])


if __name__ == '__main__':
    unittest.main() 