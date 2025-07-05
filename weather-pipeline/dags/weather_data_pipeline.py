from datetime import datetime, timedelta, timezone
import json
import gzip
import io
import time
from typing import List, Dict, Any
import pandas as pd
from airflow import DAG
from airflow.decorators import task
from airflow.providers.http.hooks.http import HttpHook
from airflow.models import Variable

default_args = {
    'owner': 'deriva',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

@task
def discover_files(**kwargs) -> List[str]:
    dag_run = kwargs.get('dag_run')
    target_years = ['2020', '2021', '2022', '2023']
    
    if dag_run and dag_run.conf:
        target_years = dag_run.conf.get('years', target_years)
    
    http_hook = HttpHook(method='GET', http_conn_id='noaa_http_default')
    
    try:
        response = http_hook.run(
            endpoint='pub/data/ghcn/daily/by_year/',
            headers={'Accept': 'text/html'}
        )
        
        files = []
        
        for year in target_years:
            filename = f"{year}.csv.gz"
            if filename in response.text:
                files.append(filename)
                
        return files
    except Exception as e:
        raise Exception(f"Failed to discover files: {str(e)}")

@task
def process_file(filename: str) -> Dict[str, Any]:
    start_time = time.time()
    http_hook = HttpHook(method='GET', http_conn_id='noaa_http_default')
    
    # Progress tracking state (inspired by LangGraph)
    processing_state = {
        'phase': 'initialization',
        'progress_percent': 0,
        'current_chunk': 0,
        'total_chunks_estimated': 0
    }
    
    try:
        processing_state['phase'] = 'downloading'
        print(f"🌐 [{processing_state['phase']}] Starting to process {filename}...")
        
        response = http_hook.run(
            endpoint=f'pub/data/ghcn/daily/by_year/{filename}',
            extra_options={'timeout': 600, 'stream': True}
        )
        print(f"📥 Downloaded {filename}, size: {len(response.content):,} bytes")
        
        processing_state['phase'] = 'processing'
        processing_state['progress_percent'] = 10
        print(f"⚙️ [{processing_state['phase']}] Processing {filename} with pandas chunking...")
        
        # Use pandas chunking for much better performance
        chunk_size = 1000000  # 1M rows per chunk - much more efficient
        total_records = 0
        unique_stations = set()
        
        # Statistics tracking
        min_date = None
        max_date = None
        measurement_counts = {'TMAX': 0, 'TMIN': 0, 'PRCP': 0}
        tmax_sum = 0.0
        tmax_count = 0
        tmin_sum = 0.0
        tmin_count = 0
        
        # Process with pandas chunking
        with gzip.open(io.BytesIO(response.content), 'rt') as f:
            chunk_number = 0
            
            # Use pandas read_csv with chunksize for efficient processing
            for chunk_df in pd.read_csv(f, header=None, chunksize=chunk_size, 
                                      names=['ID', 'DATE', 'ELEMENT', 'VALUE', 'MFLAG', 'QFLAG', 'SFLAG', 'OBSTIME'],
                                      dtype={'ID': 'str', 'DATE': 'str', 'ELEMENT': 'str', 'VALUE': 'float64'}):
                
                chunk_number += 1
                processing_state['current_chunk'] = chunk_number
                
                # Estimate progress (rough calculation)
                if chunk_number == 1:
                    # Estimate total chunks based on file size
                    estimated_rows = len(response.content) // 100  # Rough estimate
                    processing_state['total_chunks_estimated'] = max(1, estimated_rows // chunk_size)
                
                progress = min(90, 10 + (chunk_number / max(1, processing_state['total_chunks_estimated'])) * 80)
                processing_state['progress_percent'] = int(progress)
                
                print(f"📊 Chunk {chunk_number}: {len(chunk_df):,} records | Progress: {processing_state['progress_percent']}%")
                
                # Basic stats
                chunk_records = len(chunk_df)
                total_records += chunk_records
                
                # Unique stations (sample to avoid memory issues)
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
                
                # Measurement counts (vectorized)
                for element in ['TMAX', 'TMIN', 'PRCP']:
                    measurement_counts[element] += (chunk_df['ELEMENT'] == element).sum()
                
                # Temperature statistics (vectorized)
                try:
                    # TMAX processing
                    tmax_mask = (chunk_df['ELEMENT'] == 'TMAX') & chunk_df['VALUE'].notna()
                    if tmax_mask.any():
                        tmax_values = chunk_df.loc[tmax_mask, 'VALUE'] / 10.0  # Convert to Celsius
                        tmax_values = tmax_values[(tmax_values >= -100) & (tmax_values <= 100)]  # Filter outliers
                        if not tmax_values.empty:
                            tmax_sum += tmax_values.sum()
                            tmax_count += len(tmax_values)
                    
                    # TMIN processing
                    tmin_mask = (chunk_df['ELEMENT'] == 'TMIN') & chunk_df['VALUE'].notna()
                    if tmin_mask.any():
                        tmin_values = chunk_df.loc[tmin_mask, 'VALUE'] / 10.0  # Convert to Celsius
                        tmin_values = tmin_values[(tmin_values >= -100) & (tmin_values <= 100)]  # Filter outliers
                        if not tmin_values.empty:
                            tmin_sum += tmin_values.sum()
                            tmin_count += len(tmin_values)
                except Exception as temp_error:
                    print(f"⚠️ Temperature calculation warning in chunk {chunk_number}: {str(temp_error)}")
                
                # Force garbage collection every few chunks
                if chunk_number % 3 == 0:
                    import gc
                    gc.collect()
        
        processing_state['phase'] = 'finalizing'
        processing_state['progress_percent'] = 95
        print(f"✅ [{processing_state['phase']}] Finished processing {filename}: {total_records:,} total records in {chunk_number} chunks")
        
        # Calculate final statistics
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
            'total_records': int(total_records),  # Convert numpy.int64 to Python int
            'unique_stations': int(len(unique_stations)),  # Ensure Python int
            'date_range': date_range,
            'measurement_counts': {k: int(v) for k, v in measurement_counts.items()},  # Convert numpy ints
            'temperature_stats': temperature_stats,
            'processing_seconds': round(processing_time, 2),
            'processing_state': processing_state  # Include final state
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
        
        # Return error info instead of raising exception (allow partial success in reduce phase)
        return error_result

@task
def consolidate_results(results: List[Dict[str, Any]]) -> str:
    import os
    
    # Progress tracking (inspired by LangGraph state management)
    successful_files = [r for r in results if r is not None and r.get('status') != 'failed']
    failed_files = [r for r in results if r is not None and r.get('status') == 'failed']
    failed_count = len(failed_files)
    
    print(f"📊 Processing Summary:")
    print(f"✅ Successfully processed: {len(successful_files)} files")
    if failed_count > 0:
        print(f"❌ Failed: {failed_count} files")
        for failed_file in failed_files:
            print(f"   • {failed_file['file_name']}: {failed_file.get('error_type', 'Unknown')} - {failed_file.get('error', 'No details')}")
    
    # Enhanced consolidation with statistics
    consolidated = {
        'pipeline_run_id': datetime.now(timezone.utc).isoformat(),
        'processing_summary': {
            'total_files_requested': len(results),
            'successfully_processed': len(successful_files),
            'failed_files': failed_count,
            'success_rate': round(len(successful_files) / len(results) * 100, 1) if results else 0
        },
        'aggregate_statistics': {
            'total_records_across_all_files': sum(r.get('total_records', 0) for r in successful_files),
            'total_unique_stations': len(set().union(*[set(range(r.get('unique_stations', 0))) for r in successful_files])) if successful_files else 0,
            'date_range_overall': {
                'earliest': min([r['date_range']['start'] for r in successful_files if r.get('date_range', {}).get('start') != 'N/A'], default='N/A'),
                'latest': max([r['date_range']['end'] for r in successful_files if r.get('date_range', {}).get('end') != 'N/A'], default='N/A')
            },
            'average_processing_time_per_file': round(sum(r.get('processing_seconds', 0) for r in successful_files) / len(successful_files), 2) if successful_files else 0
        },
        'error_summary': [
            {
                'file_name': f['file_name'],
                'error_type': f.get('error_type', 'Unknown'),
                'error_message': f.get('error', 'No details'),
                'failed_at_phase': f.get('processing_state', {}).get('phase', 'unknown'),
                'progress_when_failed': f.get('processing_state', {}).get('progress_percent', 0)
            } for f in failed_files
        ] if failed_files else [],
        'results': successful_files
    }
    
    output_json = json.dumps(consolidated, indent=2)
    print("🎯 FINAL CONSOLIDATED RESULTS:")
    print(f"📈 Total records processed: {consolidated['aggregate_statistics']['total_records_across_all_files']:,}")
    print(f"🗓️ Date range: {consolidated['aggregate_statistics']['date_range_overall']['earliest']} to {consolidated['aggregate_statistics']['date_range_overall']['latest']}")
    print(f"⏱️ Average processing time: {consolidated['aggregate_statistics']['average_processing_time_per_file']}s per file")
    
    # Save to file on local machine (mounted volume)
    output_dir = '/opt/airflow/output'
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    filename = f'weather_pipeline_results_{timestamp}.json'
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w') as f:
        f.write(output_json)
    
    print(f"💾 Results saved to: {filepath}")
    print(f"🗂️ Local file: ./output/{filename}")
    
    return output_json

with DAG(
    'weather_data_pipeline',
    default_args=default_args,
    description='NOAA Weather Data ETL Pipeline with Dynamic Task Mapping',
    schedule=None,
    catchup=False,
    tags=['noaa', 'weather', 'etl', 'dynamic-mapping']
) as dag:
    
    files = discover_files()
    
    processed_results = process_file.expand(filename=files)
    
    final_output = consolidate_results(processed_results)
    
    files >> processed_results >> final_output 