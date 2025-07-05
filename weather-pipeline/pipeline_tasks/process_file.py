import gzip
import io
import time
from typing import Dict, Any

import pandas as pd
from airflow.decorators import task

from utils import (
    get_noaa_client,
    ProcessingConstants,
    ProcessingState,
    calculate_element_stats,
    format_file_processing_result,
    format_error_result,
    log_processing_metrics,
    log_download_metrics,
    log_chunk_progress,
    log_error_details,
    should_run_garbage_collection,
    FileProcessingError,
    handle_pipeline_error,
    safe_execute
)


@task
@handle_pipeline_error(FileProcessingError)
def process_file(filename: str) -> Dict[str, Any]:
    processing_state = ProcessingState()
    noaa_client = get_noaa_client()

    try:
        processing_state.update_phase('downloading')
        print(f"🌐 [{processing_state.phase}] Starting to process {filename}...")
        print(f"📡 Connecting to NOAA server...")
        
        download_start = time.time()
        response = noaa_client.download_file(filename)
        download_time = time.time() - download_start
        
        log_download_metrics(filename, download_time, len(response.content))
        
        processing_state.update_phase('processing', 10)
        print(f"⚙️ [{processing_state.phase}] Processing {filename} with pandas chunking...")
        
        # Initialize counters
        total_records = 0
        unique_stations = set()
        min_date = None
        max_date = None
        measurement_counts = {element: 0 for element in ProcessingConstants.MEASUREMENT_TYPES}
        tmax_sum = 0.0
        tmax_count = 0
        tmin_sum = 0.0
        tmin_count = 0

        with gzip.open(io.BytesIO(response.content), 'rt') as f:
            chunk_number = 0
            
            for chunk_df in pd.read_csv(
                f, 
                header=None, 
                chunksize=ProcessingConstants.CHUNK_SIZE,
                names=ProcessingConstants.CSV_COLUMNS,
                dtype=ProcessingConstants.CSV_DTYPES
            ):
                chunk_number += 1
                processing_state.update_progress(chunk_number)
                
                if chunk_number == 1:
                    estimated_rows = len(response.content) // 100
                    total_chunks = max(1, estimated_rows // ProcessingConstants.CHUNK_SIZE)
                    processing_state.update_progress(chunk_number, total_chunks)
                
                log_chunk_progress(chunk_number, len(chunk_df), processing_state.progress_percent)
                
                # Process chunk
                chunk_records = len(chunk_df)
                total_records += chunk_records
                
                # Update unique stations (with limit)
                if len(unique_stations) < ProcessingConstants.MAX_UNIQUE_STATIONS:
                    unique_stations.update(chunk_df['ID'].unique()[:ProcessingConstants.MAX_STATIONS_PER_CHUNK])

                # Process dates
                safe_execute(
                    _process_chunk_dates,
                    chunk_df, chunk_number,
                    default_value=(min_date, max_date),
                    log_errors=True
                )
                
                # Update min/max dates
                try:
                    chunk_df['DATE'] = pd.to_datetime(chunk_df['DATE'], format='%Y%m%d', errors='coerce')
                    valid_dates = chunk_df['DATE'].dropna()
                    if not valid_dates.empty:
                        chunk_min = valid_dates.min()
                        chunk_max = valid_dates.max()
                        if min_date is None or chunk_min < min_date:
                            min_date = chunk_min
                        if max_date is None or chunk_max > max_date:
                            max_date = chunk_max
                except Exception:
                    pass

                # Count measurements
                for element in ProcessingConstants.MEASUREMENT_TYPES:
                    measurement_counts[element] += (chunk_df['ELEMENT'] == element).sum()

                # Calculate temperature statistics
                delta_tmax_sum, delta_tmax_count = safe_execute(
                    calculate_element_stats, chunk_df, 'TMAX',
                    default_value=(0, 0)
                )
                tmax_sum += delta_tmax_sum
                tmax_count += delta_tmax_count
                
                delta_tmin_sum, delta_tmin_count = safe_execute(
                    calculate_element_stats, chunk_df, 'TMIN',
                    default_value=(0, 0)
                )
                tmin_sum += delta_tmin_sum
                tmin_count += delta_tmin_count

                # Garbage collection
                if should_run_garbage_collection(chunk_number):
                    import gc
                    gc.collect()

        processing_state.update_phase('finalizing', 95)
        print(f"✅ [{processing_state.phase}] Finished processing {filename}: {total_records:,} total records in {chunk_number} chunks")
        
        # Format results
        date_range = {
            'start': min_date.strftime('%Y-%m-%d') if min_date else 'N/A',
            'end': max_date.strftime('%Y-%m-%d') if max_date else 'N/A'
        }

        temperature_stats = {
            'avg_max_c': round(tmax_sum / tmax_count, 2) if tmax_count > 0 else 0.0,
            'avg_min_c': round(tmin_sum / tmin_count, 2) if tmin_count > 0 else 0.0
        }

        processing_time = processing_state.get_elapsed_time()
        processing_state.update_phase('completed', 100)

        result = format_file_processing_result(
            filename=filename,
            total_records=total_records,
            unique_stations=len(unique_stations),
            date_range=date_range,
            measurement_counts=measurement_counts,
            temperature_stats=temperature_stats,
            processing_seconds=processing_time,
            processing_state=processing_state
        )

        log_processing_metrics(
            filename, total_records, len(unique_stations),
            temperature_stats, processing_time
        )
        
        return result

    except Exception as e:
        processing_time = processing_state.get_elapsed_time()
        error_result = format_error_result(
            filename=filename,
            error=e,
            processing_seconds=processing_time,
            processing_state=processing_state
        )

        log_error_details(filename, e, processing_state)
        return error_result


def _process_chunk_dates(chunk_df, chunk_number):
    try:
        chunk_df['DATE'] = pd.to_datetime(chunk_df['DATE'], format='%Y%m%d', errors='coerce')
        valid_dates = chunk_df['DATE'].dropna()
        if not valid_dates.empty:
            return valid_dates.min(), valid_dates.max()
    except Exception as date_error:
        print(f"⚠️ Date parsing warning in chunk {chunk_number}: {str(date_error)}")
    return None, None
