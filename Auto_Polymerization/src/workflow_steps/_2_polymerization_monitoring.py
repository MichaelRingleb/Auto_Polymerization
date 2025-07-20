"""
_2_polymerization_monitoring.py

Polymerization monitoring module for the Auto_Polymerization workflow.
Monitors polymerization progress using NMR spectroscopy and stops the reaction
when conversion exceeds 80% or after 20 hours.

All user-editable settings (measurement intervals, conversion thresholds, NMR parameters, etc.)
should be set in users/config/platform_config.py and supplied as arguments from the controller.

All functions are designed to be called from a workflow controller script.

WORKFLOW ORDER (maintained in run_polymerization_monitoring):
1. Initialize monitoring variables and extract t0 baseline data
2. Enter monitoring loop:
   - Check maximum monitoring time
   - Perform periodic shimming (every N measurements)
   - Acquire monitoring measurement with retry logic
   - Check conversion threshold (3 consecutive measurements)
   - Wait for next measurement interval
3. Stop heating and stirring
4. Create monitoring summary
"""
from src.liquid_transfers.liquid_transfers_utils import serial_communication_error_safe_transfer_volumetric
from src.NMR.nmr_utils import (
    perform_nmr_shimming_with_retry, 
    acquire_t0_measurement_with_retry,
    acquire_and_analyze_nmr_spectrum
)
import time
import os
from datetime import datetime


# =============================================================================
# NMR SHIMMING FUNCTIONS
# =============================================================================

def perform_monitoring_shimming(medusa, max_retries=5, shim_level=1):
    """
    Perform NMR shimming during monitoring (every 4 measurements).
    
    Args:
        medusa: Medusa instance
        max_retries: Maximum number of shimming attempts
        shim_level: Shimming level (default: 1)
        
    Returns:
        dict: Shimming results with success status
    """
    medusa.logger.info("Performing monitoring NMR shimming...")
    
    shim_result = perform_nmr_shimming_with_retry(medusa, max_retries=max_retries, shim_level=shim_level)
    
    if shim_result['success']:
        medusa.logger.info("Monitoring shimming completed successfully.")
    else:
        medusa.logger.warning(f"Monitoring shimming failed: {shim_result['error_message']} - continuing with monitoring")
    
    return shim_result


# =============================================================================
# NMR MEASUREMENT FUNCTIONS
# =============================================================================

def acquire_monitoring_measurement(medusa, monitoring_params, experiment_id, iteration_counter, t0_monomer_area=None, t0_standard_area=None, nmr_data_base_path=None, experiment_start_time=None):
    """
    Acquire a single monitoring NMR measurement with retry logic.
    
    This function handles a single monitoring measurement with proper error handling
    and retry logic for both acquisition and peak detection failures.
    
    Args:
        medusa: Medusa instance
        monitoring_params: dict containing monitoring parameters
        experiment_id: Experiment identifier for filenames
        iteration_counter: Iteration counter for monitoring measurement
        t0_monomer_area: t0 monomer peak area for conversion calculation
        t0_standard_area: t0 standard peak area for conversion calculation
        nmr_data_base_path: Base path for saving NMR data
        experiment_start_time: Experiment start time for elapsed time calculation
        
    Returns:
        dict: Monitoring measurement results with success status and conversion data
    """
    from src.liquid_transfers.liquid_transfers_utils import (
        to_nmr_liquid_transfer_sampling,
        from_nmr_liquid_transfer_sampling
    )
    
    medusa.logger.info(f"Acquiring monitoring NMR measurement {iteration_counter}...")
    
    # Transfer sample to NMR
    to_nmr_liquid_transfer_sampling(medusa)
    
    # Try NMR acquisition with retry logic
    for attempt in range(3):  # 4 attempts total (0, 1, 2, 3)
        try:
            # Acquire and analyze spectrum
            result = acquire_and_analyze_nmr_spectrum(
                nmr_monomer_region=monitoring_params.get("nmr_monomer_region", (5.0, 6.0)),
                nmr_standard_region=monitoring_params.get("nmr_standard_region", (6.5, 7.5)),
                nmr_noise_region=monitoring_params.get("nmr_noise_region", (9.0, 10.0)),
                t0_monomer_area=t0_monomer_area,
                t0_standard_area=t0_standard_area,
                nmr_scans=monitoring_params.get("nmr_scans", 32),
                nmr_spectrum_center=monitoring_params.get("nmr_spectrum_center", 5),
                nmr_spectrum_width=monitoring_params.get("nmr_spectrum_width", 12),
                save_data=True,
                nmr_data_base_path=nmr_data_base_path,
                iteration_counter=iteration_counter,
                experiment_id=experiment_id,
                measurement_type="monitoring",
                experiment_start_time=experiment_start_time
            )
            
            # Check if acquisition was successful
            if result['acquisition_success'] and result['success']:
                # Transfer sample back to reaction vial
                from_nmr_liquid_transfer_sampling(medusa)
                
                medusa.logger.info(f"Monitoring measurement {iteration_counter} successful on attempt {attempt + 1}")
                return result
            else:
                raise Exception(result.get('error_message', 'Unknown acquisition error'))
                
        except Exception as e:
            error_msg = f"Monitoring measurement {iteration_counter} attempt {attempt + 1} failed: {str(e)}"
            medusa.logger.warning(error_msg)
            
            if attempt < 3:
                medusa.logger.info(f"Retrying monitoring measurement in 30 seconds...")
                time.sleep(30)
            else:
                medusa.logger.error(f"All monitoring measurement {iteration_counter} attempts failed after 4 tries")
                # Transfer sample back to reaction vial even if failed
                from_nmr_liquid_transfer_sampling(medusa)
                return {
                    'success': False,
                    'acquisition_success': False,
                    'error_message': f"Monitoring measurement {iteration_counter} failed after 4 attempts: {str(e)}",
                    'monomer_area': None,
                    'standard_area': None,
                    'monomer_standard_ratio': None,
                    'conversion': None
                }
    
    return {
        'success': False,
        'acquisition_success': False,
        'error_message': f"Monitoring measurement {iteration_counter} failed after 4 attempts",
        'monomer_area': None,
        'standard_area': None,
        'monomer_standard_ratio': None,
        'conversion': None
    }


# =============================================================================
# DATA ANALYSIS AND REPORTING FUNCTIONS
# =============================================================================

def create_monitoring_summary(experiment_id, t0_baseline, monitoring_results, monitoring_params, base_path=None):
    """
    Create a comprehensive monitoring summary file with timing and conversion data.
    
    Args:
        experiment_id: Experiment identifier
        t0_baseline: t0 baseline data from polymerization setup
        monitoring_results: List of monitoring measurement results
        monitoring_params: dict containing monitoring parameters
        base_path: Base path for saving summary file (should be users/data)
        
    Returns:
        str: Path to the created summary file (saved directly in data folder, not subfolder)
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    summary_filename = f"polymerization_monitoring_summary_{experiment_id}_{timestamp}.txt"
    
    # Ensure summary file is saved directly in the data folder (not in a subfolder)
    if base_path:
        summary_path = os.path.join(base_path, summary_filename)
    else:
        summary_path = summary_filename
    
    # Create the directory if it doesn't exist
    if base_path and not os.path.exists(base_path):
        os.makedirs(base_path, exist_ok=True)
    
    with open(summary_path, 'w') as f:
        f.write(f"POLYMERIZATION MONITORING SUMMARY\n")
        f.write(f"Experiment ID: {experiment_id}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"{'='*60}\n\n")
        
        # t0 Baseline Information
        f.write(f"T0 BASELINE MEASUREMENTS\n")
        f.write(f"{'-'*40}\n")
        if t0_baseline and t0_baseline['success']:
            f.write(f"Successful measurements: {t0_baseline['successful_count']}/{t0_baseline['total_count']}\n")
            f.write(f"Average monomer area: {t0_baseline['average_monomer_area']:.2f}\n")
            f.write(f"Average standard area: {t0_baseline['average_standard_area']:.2f}\n")
            f.write(f"Average ratio: {t0_baseline['average_ratio']:.4f}\n\n")
            
            # Individual t0 measurements
            f.write(f"Individual t0 measurements:\n")
            for i, measurement in enumerate(t0_baseline['individual_measurements']):
                if measurement['success']:
                    f.write(f"  t0_{i+1}: Monomer={measurement['monomer_area']:.2f}, Standard={measurement['standard_area']:.2f}, Ratio={measurement['monomer_standard_ratio']:.4f}\n")
                else:
                    f.write(f"  t0_{i+1}: FAILED - {measurement.get('error_message', 'Unknown error')}\n")
            f.write(f"\n")
        else:
            f.write(f"T0 baseline acquisition failed: {t0_baseline.get('error_message', 'Unknown error') if t0_baseline else 'No t0 data provided'}\n\n")
        
        # Monitoring Parameters
        f.write(f"MONITORING PARAMETERS\n")
        f.write(f"{'-'*40}\n")
        f.write(f"Measurement interval: {monitoring_params.get('measurement_interval_minutes', 10)} minutes\n")
        f.write(f"Shimming interval: {monitoring_params.get('shimming_interval', 4)} measurements\n")
        f.write(f"Conversion threshold: {monitoring_params.get('conversion_threshold', 80)}%\n")
        f.write(f"Maximum monitoring time: {monitoring_params.get('max_monitoring_hours', 20)} hours\n")
        f.write(f"NMR scans: {monitoring_params.get('nmr_scans', 32)}\n")
        f.write(f"Monomer region: {monitoring_params.get('nmr_monomer_region', (5.0, 6.0))} ppm\n")
        f.write(f"Standard region: {monitoring_params.get('nmr_standard_region', (6.5, 7.5))} ppm\n")
        f.write(f"Noise region: {monitoring_params.get('nmr_noise_region', (9.0, 10.0))} ppm\n\n")
        
        # Monitoring Results
        f.write(f"MONITORING RESULTS\n")
        f.write(f"{'-'*40}\n")
        f.write(f"Total measurements: {len(monitoring_results)}\n")
        successful_measurements = [r for r in monitoring_results if r['success']]
        f.write(f"Successful measurements: {len(successful_measurements)}\n")
        failed_measurements = [r for r in monitoring_results if not r['success']]
        f.write(f"Failed measurements: {len(failed_measurements)}\n\n")
        
        if successful_measurements:
            f.write(f"Measurement Details:\n")
            f.write(f"{'Iter':<6} {'Time':<20} {'Monomer':<10} {'Standard':<10} {'Ratio':<10} {'Conversion':<12} {'Status':<10}\n")
            f.write(f"{'-'*80}\n")
            
            for i, result in enumerate(monitoring_results):
                timestamp = result.get('timestamp', 'Unknown')
                if result['success']:
                    monomer_area = result.get('monomer_area', 0)
                    standard_area = result.get('standard_area', 0)
                    ratio = result.get('monomer_standard_ratio', 0)
                    conversion = result.get('conversion', 0)
                    status = 'SUCCESS'
                else:
                    monomer_area = standard_area = ratio = conversion = 0
                    status = 'FAILED'
                
                f.write(f"{i+1:<6} {timestamp:<20} {monomer_area:<10.2f} {standard_area:<10.2f} {ratio:<10.4f} {conversion:<12.2f} {status:<10}\n")
            
            f.write(f"\n")
            
            # Conversion Analysis
            conversions = [r.get('conversion', 0) for r in successful_measurements if r.get('conversion') is not None]
            if conversions:
                f.write(f"CONVERSION ANALYSIS\n")
                f.write(f"{'-'*40}\n")
                f.write(f"Final conversion: {conversions[-1]:.2f}%\n")
                f.write(f"Maximum conversion: {max(conversions):.2f}%\n")
                f.write(f"Average conversion: {sum(conversions)/len(conversions):.2f}%\n")
                
                # Check if conversion threshold was reached
                threshold = monitoring_params.get('conversion_threshold', 80)
                if max(conversions) >= threshold:
                    f.write(f"Conversion threshold ({threshold}%) was reached.\n")
                else:
                    f.write(f"Conversion threshold ({threshold}%) was not reached.\n")
        
        # Error Summary
        if failed_measurements:
            f.write(f"\nERROR SUMMARY\n")
            f.write(f"{'-'*40}\n")
            for i, result in enumerate(failed_measurements):
                f.write(f"Measurement {i+1}: {result.get('error_message', 'Unknown error')}\n")
    
    return summary_path


# =============================================================================
# REACTION CONTROL FUNCTIONS
# =============================================================================

def stop_polymerization_reaction(medusa):
    """
    Stop the polymerization reaction by cooling down and stopping stirring.
    
    Args:
        medusa: Medusa instance
    """
    medusa.logger.info("Stopping heating and stirring...")
    medusa.set_hotplate_temperature("Reaction_Vial", 25)  # Cool down
    medusa.set_hotplate_rpm("Reaction_Vial", 0)  # Stop stirring
    medusa.logger.info("Polymerization reaction stopped.")


# =============================================================================
# MAIN WORKFLOW FUNCTION
# =============================================================================

def run_polymerization_monitoring(medusa, monitoring_params, experiment_id, t0_baseline=None, nmr_data_base_path=None, data_base_path=None):
    """
    Execute the complete polymerization monitoring workflow.
    
    WORKFLOW ORDER:
    1. Initialize monitoring variables and extract t0 baseline data
    2. Enter monitoring loop:
       - Check maximum monitoring time
       - Perform periodic shimming (every N measurements)
       - Acquire monitoring measurement with retry logic
       - Check conversion threshold (3 consecutive measurements)
       - Wait for next measurement interval
    3. Stop heating and stirring
    4. Create monitoring summary
    
    Args:
        medusa: Medusa instance
        monitoring_params: dict containing all monitoring parameters
        experiment_id: Experiment identifier for filenames
        t0_baseline: t0 baseline data from polymerization setup
        nmr_data_base_path: Base path for saving NMR data
        data_base_path: Base path for saving summary files
        
    Returns:
        dict: Complete monitoring results including summary file path
    """
    medusa.logger.info("Starting polymerization monitoring...")
    
    # Step 1: Extract monitoring parameters
    measurement_interval = monitoring_params.get("measurement_interval_minutes", 10) * 60  # Convert to seconds
    shimming_interval = monitoring_params.get("shimming_interval", 4)
    conversion_threshold = monitoring_params.get("conversion_threshold", 80)
    max_monitoring_time = monitoring_params.get("max_monitoring_hours", 20) * 3600  # Convert to seconds
    
    # Step 2: Initialize monitoring variables
    iteration_counter = 0
    monitoring_results = []
    start_time = time.time()
    last_shim_time = start_time
    
    # Step 3: Extract t0 baseline data for conversion calculation
    t0_monomer_area = None
    t0_standard_area = None
    if t0_baseline and t0_baseline['success']:
        t0_monomer_area = t0_baseline['average_monomer_area']
        t0_standard_area = t0_baseline['average_standard_area']
        medusa.logger.info(f"Using t0 baseline: Monomer={t0_monomer_area:.2f}, Standard={t0_standard_area:.2f}")
    else:
        medusa.logger.warning("No valid t0 baseline provided - conversion calculation will be approximate")
    
    # Step 4: Monitoring loop
    while True:
        iteration_counter += 1
        current_time = time.time()
        elapsed_time = current_time - start_time
        
        medusa.logger.info(f"Monitoring iteration {iteration_counter} (elapsed: {elapsed_time/3600:.1f}h)")
        
        # Check if maximum monitoring time exceeded
        if elapsed_time >= max_monitoring_time:
            medusa.logger.info(f"Maximum monitoring time ({max_monitoring_time/3600:.1f}h) reached - stopping monitoring")
            break
        
        # Perform shimming if needed
        if iteration_counter % shimming_interval == 1 and iteration_counter > 1:
            medusa.logger.info(f"Performing periodic shimming (every {shimming_interval} measurements)")
            shim_result = perform_monitoring_shimming(medusa, max_retries=3, shim_level=1)
            if not shim_result['success']:
                medusa.logger.warning("Periodic shimming failed - continuing with monitoring")
        
        # Acquire monitoring measurement
        measurement_result = acquire_monitoring_measurement(
            medusa, monitoring_params, experiment_id, iteration_counter,
            t0_monomer_area=t0_monomer_area, t0_standard_area=t0_standard_area, 
            nmr_data_base_path=nmr_data_base_path, experiment_start_time=start_time
        )
        
        # Add timestamp to result
        measurement_result['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        monitoring_results.append(measurement_result)
        
        # Check if measurement was successful
        if measurement_result['success']:
            conversion = measurement_result.get('conversion', 0)
            medusa.logger.info(f"Measurement {iteration_counter} successful - Conversion: {conversion:.2f}%")
            
            # Check if conversion threshold reached (3 consecutive measurements)
            if conversion >= conversion_threshold:
                # Check if we have 3 consecutive measurements above threshold
                recent_conversions = []
                for i in range(max(0, len(monitoring_results)-3), len(monitoring_results)):
                    if monitoring_results[i]['success']:
                        recent_conversions.append(monitoring_results[i].get('conversion', 0))
                
                if len(recent_conversions) >= 3 and all(c >= conversion_threshold for c in recent_conversions[-3:]):
                    medusa.logger.info(f"Conversion threshold ({conversion_threshold}%) reached in 3 consecutive measurements - stopping monitoring")
                    break
        else:
            medusa.logger.warning(f"Measurement {iteration_counter} failed: {measurement_result.get('error_message', 'Unknown error')}")
        
        # Wait for next measurement interval
        if iteration_counter < max_monitoring_time / measurement_interval:  # Don't wait after last measurement
            medusa.logger.info(f"Waiting {measurement_interval/60:.1f} minutes until next measurement...")
            time.sleep(measurement_interval)
    
    # Step 5: Stop heating and stirring
    stop_polymerization_reaction(medusa)
    
    # Step 6: Create monitoring summary
    summary_path = create_monitoring_summary(experiment_id, t0_baseline, monitoring_results, monitoring_params, data_base_path)
    medusa.logger.info(f"Monitoring summary saved to: {summary_path}")
    
    medusa.logger.info("Polymerization monitoring completed.")
    
    return {
        'success': True,
        'total_measurements': len(monitoring_results),
        'successful_measurements': len([r for r in monitoring_results if r['success']]),
        'failed_measurements': len([r for r in monitoring_results if not r['success']]),
        'final_conversion': monitoring_results[-1].get('conversion', 0) if monitoring_results and monitoring_results[-1]['success'] else None,
        'summary_file': summary_path,
        'monitoring_results': monitoring_results
    } 