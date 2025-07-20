import time
import os
import csv
from datetime import datetime
import users.config.platform_config as config
from src.NMR.nmr_utils import acquire_and_analyze_nmr_spectrum, perform_nmr_shimming_with_retry, monomer_removal_dialysis
from src.liquid_transfers.liquid_transfers_utils import (
    serial_communication_error_safe_transfer_volumetric,
    to_nmr_liquid_transfer_sampling,
    from_nmr_liquid_transfer_sampling
)


def run_dialysis_workflow(medusa, logger=None):
    """
    Runs the dialysis workflow using parameters from users/config/platform_config.py.
    Handles both noise-comparison-based and time-based stopping.
    Updates summary files (txt and CSV) after each measurement.
    Handles errors, retries, shimming, and keyboard interrupts gracefully.
    Returns a summary dictionary.
    """
    # --- Load config values ---
    experiment_id = getattr(config, 'experiment_id', 'UNKNOWN')
    dialysis_params = getattr(config, 'dialysis_params', {})
    nmr_transfer_params = getattr(config, 'nmr_transfer_params', {})
    monitoring_params = getattr(config, 'polymerization_monitoring_params', {})
    nmr_data_base_path = getattr(config, 'nmr_data_base_path', 'Auto_Polymerization/users/data/NMR_data')
    data_base_path = getattr(config, 'data_base_path', 'Auto_Polymerization/users/data')
    nmr_monomer_region = monitoring_params.get('nmr_monomer_region', (5.0, 6.0))
    nmr_noise_region = monitoring_params.get('nmr_noise_region', (9.0, 10.0))
    shimming_interval = monitoring_params.get('shimming_interval', 4)
    sample_volume = nmr_transfer_params.get('sample_volume_ml', 2.1)
    noise_comparison_based = dialysis_params.get('noise_comparison_based', True)
    time_based = dialysis_params.get('time_based', True)
    dialysis_duration_mins = dialysis_params.get('dialysis_duration_mins', 240)


    # --- Initialize summary data ---
    start_time = datetime.now()
    start_time_str = start_time.strftime('%Y-%m-%d_%H-%M-%S')
    summary_txt = os.path.join(data_base_path, f'dialysis_summary_{experiment_id}_{start_time_str}.txt')
    summary_csv = os.path.join(data_base_path, f'dialysis_summary_{experiment_id}_{start_time_str}.csv')
    nmr_results = []
    error_log = []
    dialysis_start = time.time()
    elapsed_minutes = 0
    iteration_counter = 0
    stop_reason = None
    below_threshold = False
    interrupted = False

    # --- Start peristaltic pumps ---
    medusa.log_info('Starting dialysis peristaltic pumps...')
    medusa.transfer_continuous(source="Reaction_Vial", target="Reaction_Vial", pump_id="Polymer_Peri_Pump", direction_CW=False, transfer_rate=0.7)
    medusa.transfer_continuous(source="Elution_Solvent_Vessel", target="Waste_Vessel", pump_id="Solvent_Peri_Pump", direction_CW=True, transfer_rate=0.7)

    try:
        while True:
            iteration_counter += 1
            elapsed_minutes = int((time.time() - dialysis_start) / 60)
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            medusa.log_info(f"Dialysis iteration {iteration_counter} (elapsed: {elapsed_minutes} min)")
            # --- Transfer sample to NMR ---
            try:
                to_nmr_liquid_transfer_sampling(medusa)
            except Exception as e:
                error_log.append({
                    'timestamp': timestamp, 'iteration': iteration_counter,
                    'error_type': 'Transfer', 'error_message': str(e),
                    'retry_count': 0, 'additional_info': 'To NMR'
                })
                medusa.log_error(f"Sample transfer to NMR failed: {e}")
                continue

            # --- NMR acquisition with retry logic ---
            nmr_success = False
            nmr_retries = 0
            max_nmr_retries = 3
            nmr_result = None
            filename = f"{experiment_id}_{timestamp}_dialysis_{iteration_counter}_t{elapsed_minutes}"
            while not nmr_success and nmr_retries <= max_nmr_retries:
                try:
                    nmr_result = acquire_and_analyze_nmr_spectrum(
                        nmr_monomer_region=nmr_monomer_region,
                        nmr_standard_region=None,  # Not used for dialysis
                        nmr_noise_region=nmr_noise_region,
                        nmr_scans=monitoring_params.get('nmr_scans', 32),
                        nmr_spectrum_center=monitoring_params.get('nmr_spectrum_center', 5),
                        nmr_spectrum_width=monitoring_params.get('nmr_spectrum_width', 12),
                        save_data=True,
                        nmr_data_base_path=nmr_data_base_path,
                        iteration_counter=iteration_counter,
                        experiment_id=experiment_id,
                        measurement_type="dialysis",
                        experiment_start_time=dialysis_start,
                        filename_override=filename,
                        medusa=medusa
                    )
                    nmr_success = nmr_result.get('acquisition_success', False)
                    if not nmr_success:
                        raise Exception(nmr_result.get('error_message', 'Unknown NMR error'))
                except Exception as e:
                    nmr_retries += 1
                    error_log.append({
                        'timestamp': timestamp, 'iteration': iteration_counter,
                        'error_type': 'NMR', 'error_message': str(e),
                        'retry_count': nmr_retries, 'additional_info': 'acquire_and_analyze_nmr_spectrum'
                    })
                    medusa.log_warn(f"NMR acquisition failed (retry {nmr_retries}): {e}")
                    if nmr_retries > max_nmr_retries:
                        medusa.log_error(f"NMR acquisition failed after {max_nmr_retries} retries. Skipping iteration.")
                        break
                    time.sleep(10)

            if not nmr_success:
                continue

            # --- Analyze for monomer removal threshold ---
            try:
                # Use monomer_removal_dialysis to check threshold
                dialysis_analysis = monomer_removal_dialysis(
                    integration_txt_path=None,  # Not used here
                    nmr_data_folder=nmr_data_base_path,
                    noise_region=nmr_noise_region,
                    ppm_suffix='_freq_ppm.npy',
                    spec_suffix='_spec.npy',
                )
                # Find the result for the current filename
                this_result = None
                for r in dialysis_analysis:
                    if filename in r.get('Filename', ''):
                        this_result = r
                        break
                if this_result:
                    monomer_peak = this_result.get('Peak_Height', None)
                    noise_level = this_result.get('Noise_Level', None)
                    ratio = this_result.get('Height/Noise_Ratio', None)
                    below_threshold = this_result.get('Above_2x_Noise', False) == False
                else:
                    monomer_peak = None
                    noise_level = None
                    ratio = None
                    below_threshold = False
            except Exception as e:
                error_log.append({
                    'timestamp': timestamp, 'iteration': iteration_counter,
                    'error_type': 'Analysis', 'error_message': str(e),
                    'retry_count': 0, 'additional_info': 'monomer_removal_dialysis'
                })
                medusa.log_warn(f"Dialysis analysis failed: {e}")
                monomer_peak = None
                noise_level = None
                ratio = None
                below_threshold = False

            # --- Transfer sample back ---
            try:
                from_nmr_liquid_transfer_sampling(medusa)
            except Exception as e:
                error_log.append({
                    'timestamp': timestamp, 'iteration': iteration_counter,
                    'error_type': 'Transfer', 'error_message': str(e),
                    'retry_count': 0, 'additional_info': 'From NMR'
                })
                medusa.log_error(f"Sample transfer from NMR failed: {e}")

            # --- Save NMR result ---
            nmr_results.append({
                'iteration': iteration_counter,
                'timestamp': timestamp,
                'elapsed_min': elapsed_minutes,
                'monomer_peak': monomer_peak,
                'noise_level': noise_level,
                'ratio': ratio,
                'below_3x_noise': below_threshold,
                'nmr_filename': filename
            })

            # --- Shimming if needed ---
            if shimming_interval and iteration_counter % shimming_interval == 0:
                shim_success = False
                shim_retries = 0
                max_shim_retries = 3
                while not shim_success and shim_retries <= max_shim_retries:
                    try:
                        shim_result = perform_nmr_shimming_with_retry(medusa, max_retries=1)
                        shim_success = shim_result.get('success', False)
                        if not shim_success:
                            raise Exception(shim_result.get('error_message', 'Unknown shimming error'))
                    except Exception as e:
                        shim_retries += 1
                        error_log.append({
                            'timestamp': timestamp, 'iteration': iteration_counter,
                            'error_type': 'Shim', 'error_message': str(e),
                            'retry_count': shim_retries, 'additional_info': 'perform_nmr_shimming_with_retry'
                        })
                        medusa.log_warn(f"Shimming failed (retry {shim_retries}): {e}")
                        if shim_retries > max_shim_retries:
                            medusa.log_error(f"Shimming failed after {max_shim_retries} retries. Continuing without shimming.")
                            break
                        time.sleep(10)

            # --- Update summary files ---
            write_dialysis_summary_txt(summary_txt, experiment_id, start_time, nmr_results, error_log, dialysis_params, monitoring_params, nmr_transfer_params)
            write_dialysis_summary_csv(summary_csv, nmr_results, error_log)

            # --- Check stop conditions ---
            if noise_comparison_based and below_threshold:
                stop_reason = 'noise-comparison-based (monomer < 3x noise)'
                break
            if time_based and elapsed_minutes >= dialysis_duration_mins:
                stop_reason = 'time-based (duration reached)'
                break

            # --- Wait before next iteration ---
            measurement_interval = dialysis_params.get("dialysis_measurement_interval_minutes")
            if measurement_interval is None:
                measurement_interval = monitoring_params.get("measurement_interval_minutes", 10)
            measurement_interval_sec = measurement_interval * 60
            time.sleep(measurement_interval_sec)

    except KeyboardInterrupt:
        interrupted = True
        stop_reason = 'KeyboardInterrupt (user stopped)'
        medusa.log_warn('Dialysis workflow interrupted by user. Finishing current measurement and stopping.')

    # --- Stop peristaltic pumps and flush polymer back to reaction vial---
    medusa.log_info('Stopping peristaltic pumps and flushing lines...')
    medusa.transfer_continuous(source="Reaction_Vial", target="Waste_Vessel", pump_id="Polymer_Peri_Pump", direction_CW=True, transfer_rate=0.7)
    medusa.transfer_continuous(source="Elution_Solvent_Vessel", target="Waste_Vessel", pump_id="Solvent_Peri_Pump", direction_CW=False, transfer_rate=0)
    time.sleep(600)  # Wait 10 min to pump fully empty
    medusa.transfer_continuous(source="Elution_Solvent_Vessel", target="Waste_Vessel", pump_id="Polymer_Peri_Pump", direction_CW=True, transfer_rate=0)

    end_time = datetime.now()
    medusa.log_info(f"Dialysis workflow completed. Reason: {stop_reason}")
    write_dialysis_summary_txt(summary_txt, experiment_id, start_time, nmr_results, error_log, dialysis_params, monitoring_params, nmr_transfer_params, end_time=end_time, stop_reason=stop_reason)
    write_dialysis_summary_csv(summary_csv, nmr_results, error_log)

    return {
        'success': True,
        'nmr_results': nmr_results,
        'error_log': error_log,
        'summary_txt': summary_txt,
        'summary_csv': summary_csv,
        'stop_reason': stop_reason,
        'interrupted': interrupted,
        'start_time': start_time,
        'end_time': end_time
    }


def write_dialysis_summary_txt(filepath, experiment_id, start_time, nmr_results, error_log, dialysis_params, monitoring_params, nmr_transfer_params, end_time=None, stop_reason=None):
    """Writes the dialysis summary as a plain text file."""
    with open(filepath, 'w') as f:
        f.write(f"DIALYSIS SUMMARY\n")
        f.write(f"Experiment ID: {experiment_id}\n")
        f.write(f"Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        if end_time:
            f.write(f"End Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        if stop_reason:
            f.write(f"Stop Reason: {stop_reason}\n")
        f.write(f"Dialysis Duration (min): {dialysis_params.get('dialysis_duration_mins', 'N/A')}\n")
        f.write(f"Shimming Interval: {monitoring_params.get('shimming_interval', 'N/A')}\n")
        f.write(f"Sample Volume (mL): {nmr_transfer_params.get('sample_volume_ml', 'N/A')}\n")
        f.write(f"NMR Monomer Region: {monitoring_params.get('nmr_monomer_region', 'N/A')}\n")
        f.write(f"NMR Noise Region: {monitoring_params.get('nmr_noise_region', 'N/A')}\n")
        f.write(f"Stop Condition: {'noise-comparison-based' if dialysis_params.get('noise_comparison_based') else ''}{' and ' if dialysis_params.get('noise_comparison_based') and dialysis_params.get('time_based') else ''}{'time-based' if dialysis_params.get('time_based') else ''}\n")
        f.write("-"*60 + "\n\n")
        f.write("Iter | Timestamp           | Elapsed (min) | Monomer Peak | Noise Level | Ratio   | Below 3x Noise | NMR Filename\n")
        f.write("-"*95 + "\n")
        for r in nmr_results:
            f.write(f"{r['iteration']:<4} | {r['timestamp']:<18} | {r['elapsed_min']:<13} | {r['monomer_peak']!s:<12} | {r['noise_level']!s:<10} | {r['ratio']!s:<7} | {str(r['below_3x_noise']):<14} | {r['nmr_filename']}\n")
        f.write("\n\n\n\n")
        f.write("==== ERROR/RETRY LOG ====\n")
        f.write("Timestamp           | Iter | Error Type | Error Message                  | Retry Count | Additional Info\n")
        f.write("-"*95 + "\n")
        for e in error_log:
            f.write(f"{e['timestamp']:<18} | {e['iteration']:<4} | {e['error_type']:<9} | {e['error_message']:<30} | {e['retry_count']:<11} | {e['additional_info']}\n")


def write_dialysis_summary_csv(filepath, nmr_results, error_log):
    """Writes the dialysis summary as a CSV file (main table, blank lines, error table)."""
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        # Main NMR results table
        writer.writerow(["Iter", "Timestamp", "Elapsed (min)", "Monomer Peak", "Noise Level", "Ratio", "Below 3x Noise", "NMR Filename"])
        for r in nmr_results:
            writer.writerow([
                r['iteration'], r['timestamp'], r['elapsed_min'], r['monomer_peak'],
                r['noise_level'], r['ratio'], r['below_3x_noise'], r['nmr_filename']
            ])
        # Four blank lines
        for _ in range(4):
            writer.writerow([])
        # Error/retry log
        writer.writerow(["Error Timestamp", "Iter", "Error Type", "Error Message", "Retry Count", "Additional Info"])
        for e in error_log:
            writer.writerow([
                e['timestamp'], e['iteration'], e['error_type'], e['error_message'], e['retry_count'], e['additional_info']
            ])
