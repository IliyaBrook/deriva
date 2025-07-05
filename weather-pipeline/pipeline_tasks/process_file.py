import gzip
import io
import time
from datetime import datetime, timezone
from typing import Dict, Any

import pandas as pd
from airflow.decorators import task
from airflow.providers.http.hooks.http import HttpHook

from utils.calculate_element_stats import calculate_element_stats


@task
def process_file(filename: str) -> Dict[str, Any]:
    start_time = time.time()
    http_hook = HttpHook(method='GET', http_conn_id='noaa_http_default')

    processing_state = {
        'phase': 'initialization',
        'progress_percent': 0,
        'current_chunk': 0,
        'total_chunks_estimated': 0
    }

    try:
        processing_state['phase'] = 'downloading'
        print(f"🌐 [{processing_state['phase']}] Starting to process {filename}...")
        print(f"📡 Connecting to NOAA server...")

        download_start = time.time()
        response = http_hook.run(
            endpoint=f'pub/data/ghcn/daily/by_year/{filename}',
            extra_options={'timeout': 1800, 'stream': True}
        )
        download_time = time.time() - download_start
        file_size_mb = len(response.content) / (1024 * 1024)
        print(f"📥 Downloaded {filename} in {download_time:.1f}s")
        print(f"📊 File size: {file_size_mb:.1f} MB ({len(response.content):,} bytes)")

        processing_state['phase'] = 'processing'
        processing_state['progress_percent'] = 10
        print(f"⚙️ [{processing_state['phase']}] Processing {filename} with pandas chunking...")

        chunk_size = 1000000
        total_records = 0
        unique_stations = set()

        min_date = None
        max_date = None
        measurement_counts = {'TMAX': 0, 'TMIN': 0, 'PRCP': 0}
        tmax_sum = 0.0
        tmax_count = 0
        tmin_sum = 0.0
        tmin_count = 0

        with gzip.open(io.BytesIO(response.content), 'rt') as f:
            chunk_number = 0

            for chunk_df in pd.read_csv(f, header=None, chunksize=chunk_size,
                                        names=['ID', 'DATE', 'ELEMENT', 'VALUE', 'MFLAG', 'QFLAG', 'SFLAG', 'OBSTIME'],
                                        dtype={'ID': 'str', 'DATE': 'str', 'ELEMENT': 'str', 'VALUE': 'float64'}):

                chunk_number += 1
                processing_state['current_chunk'] = chunk_number

                if chunk_number == 1:
                    estimated_rows = len(response.content) // 100
                    processing_state['total_chunks_estimated'] = max(1, estimated_rows // chunk_size)

                # noinspection PyTypeChecker
                progress = min(90, 10 + (chunk_number / max(1, processing_state['total_chunks_estimated'])) * 80)
                processing_state['progress_percent'] = int(progress)

                print(f"📊 Chunk {chunk_number}: {len(chunk_df):,} records | Progress: {processing_state['progress_percent']}%")

                chunk_records = len(chunk_df)
                total_records += chunk_records

                if len(unique_stations) < 100000:
                    unique_stations.update(chunk_df['ID'].unique()[:1000])  # Limit per chunk

                # Date processing
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
                except Exception as date_error:
                    print(f"⚠️ Date parsing warning in chunk {chunk_number}: {str(date_error)}")

                for element in ['TMAX', 'TMIN', 'PRCP']:
                    # noinspection PyUnresolvedReferences
                    measurement_counts[element] += (chunk_df['ELEMENT'] == element).sum()


                try:
                    delta_tmax_sum, delta_tmax_count = calculate_element_stats(chunk_df, 'TMAX')
                    tmax_sum += delta_tmax_sum
                    tmax_count += delta_tmax_count

                    delta_tmin_sum, delta_tmin_count = calculate_element_stats(chunk_df, 'TMIN')
                    tmin_sum += delta_tmin_sum
                    tmin_count += delta_tmin_count

                except Exception as temp_error:
                    print(f"⚠️ Temperature calculation warning in chunk {chunk_number}: {str(temp_error)}")

                if chunk_number % 3 == 0:
                    import gc
                    gc.collect()

        processing_state['phase'] = 'finalizing'
        processing_state['progress_percent'] = 95
        print(f"✅ [{processing_state['phase']}] Finished processing {filename}: {total_records:,} total records in {chunk_number} chunks")

        date_range = {
            'start': min_date.strftime('%Y-%m-%d') if min_date else 'N/A',
            'end': max_date.strftime('%Y-%m-%d') if max_date else 'N/A'
        }

        temperature_stats = {
            'avg_max_c': round(tmax_sum / tmax_count, 2) if tmax_count > 0 else 0.0,
            'avg_min_c': round(tmin_sum / tmin_count, 2) if tmin_count > 0 else 0.0
        }

        processing_time = time.time() - start_time
        processing_state['progress_percent'] = 100

        result = {
            'file_name': filename,
            'processed_at': datetime.now(timezone.utc).isoformat(),
            'total_records': int(total_records),
            'unique_stations': int(len(unique_stations)),
            'date_range': date_range,
            'measurement_counts': {k: int(v) for k, v in measurement_counts.items()},  # Convert numpy ints
            'temperature_stats': temperature_stats,
            'processing_seconds': round(processing_time, 2),
            'processing_state': processing_state
        }

        print(f"🎉 Successfully processed {filename} in {processing_time:.1f}s!")
        print(f"📊 Final stats: {total_records:,} records, {len(unique_stations):,} stations")
        print(f"🌡️  Temperatures: TMAX avg {temperature_stats['avg_max_c']}°C, TMIN avg {temperature_stats['avg_min_c']}°C")
        return result

    except Exception as e:
        processing_time = time.time() - start_time
        error_result = {
            'file_name': filename,
            'processed_at': datetime.now(timezone.utc).isoformat(),
            'error': str(e),
            'error_type': type(e).__name__,
            'processing_seconds': round(processing_time, 2),
            'processing_state': {k: int(v) if isinstance(v, (int, float)) and k != 'phase' else v for k, v in processing_state.items()},  # Ensure Python types
            'status': 'failed'
        }

        print(f"❌ Failed to process {filename} in phase '{processing_state['phase']}': {str(e)}")
        print(f"🔍 Error details: {type(e).__name__} at {processing_state['progress_percent']}% completion")

        return error_result
