import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Any

from airflow.decorators import task

from utils import get_current_timestamp, ConsolidationError, handle_pipeline_error


@task
@handle_pipeline_error(ConsolidationError)
def consolidate_results(results: List[Dict[str, Any]]) -> str:
    successful_files = [r for r in results if r is not None and r.get('status') != 'failed']
    failed_files = [r for r in results if r is not None and r.get('status') == 'failed']
    failed_count = len(failed_files)

    print(f"📊 Processing Summary:")
    print(f"✅ Successfully processed: {len(successful_files)} files")
    if failed_count > 0:
        print(f"❌ Failed: {failed_count} files")
        for failed_file in failed_files:
            print(f"   • {failed_file['file_name']}: {failed_file.get('error_type', 'Unknown')} - {failed_file.get('error', 'No details')}")

    consolidated = _build_consolidated_report(results, successful_files, failed_files)
    output_json = json.dumps(consolidated, indent=2)
    
    _log_final_metrics(consolidated)
    filepath = _save_results_to_file(output_json)
    
    print(f"💾 Results saved to: {filepath}")
    print(f"🗂️ Local file: ./output/{os.path.basename(filepath)}")

    return output_json


def _build_consolidated_report(results: List[Dict[str, Any]], successful_files: List[Dict[str, Any]], failed_files: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        'pipeline_run_id': get_current_timestamp(),
        'processing_summary': {
            'total_files_requested': len(results),
            'successfully_processed': len(successful_files),
            'failed_files': len(failed_files),
            'success_rate': round(len(successful_files) / len(results) * 100, 1) if results else 0
        },
        'aggregate_statistics': _calculate_aggregate_statistics(successful_files),
        'error_summary': _build_error_summary(failed_files),
        'results': successful_files
    }


def _calculate_aggregate_statistics(successful_files: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not successful_files:
        return {
            'total_records_across_all_files': 0,
            'total_unique_stations': 0,
            'date_range_overall': {'earliest': 'N/A', 'latest': 'N/A'},
            'average_processing_time_per_file': 0
        }
    
    total_records = sum(r.get('total_records', 0) for r in successful_files)
    
    # Calculate unique stations (approximation)
    total_unique_stations = len(set().union(*[
        set(range(r.get('unique_stations', 0))) 
        for r in successful_files
    ]))
    
    # Calculate date range
    valid_start_dates = [
        r['date_range']['start'] 
        for r in successful_files 
        if r.get('date_range', {}).get('start') != 'N/A'
    ]
    valid_end_dates = [
        r['date_range']['end'] 
        for r in successful_files 
        if r.get('date_range', {}).get('end') != 'N/A'
    ]
    
    date_range_overall = {
        'earliest': min(valid_start_dates) if valid_start_dates else 'N/A',
        'latest': max(valid_end_dates) if valid_end_dates else 'N/A'
    }
    
    average_processing_time = round(
        sum(r.get('processing_seconds', 0) for r in successful_files) / len(successful_files), 2
    )
    
    return {
        'total_records_across_all_files': total_records,
        'total_unique_stations': total_unique_stations,
        'date_range_overall': date_range_overall,
        'average_processing_time_per_file': average_processing_time
    }


def _build_error_summary(failed_files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not failed_files:
        return []
    
    return [
        {
            'file_name': f['file_name'],
            'error_type': f.get('error_type', 'Unknown'),
            'error_message': f.get('error', 'No details'),
            'failed_at_phase': f.get('processing_state', {}).get('phase', 'unknown'),
            'progress_when_failed': f.get('processing_state', {}).get('progress_percent', 0)
        } for f in failed_files
    ]


def _log_final_metrics(consolidated: Dict[str, Any]):
    print("🎯 FINAL CONSOLIDATED RESULTS:")
    print(f"📈 Total records processed: {consolidated['aggregate_statistics']['total_records_across_all_files']:,}")
    print(f"🗓️ Date range: {consolidated['aggregate_statistics']['date_range_overall']['earliest']} to {consolidated['aggregate_statistics']['date_range_overall']['latest']}")
    print(f"⏱️ Average processing time: {consolidated['aggregate_statistics']['average_processing_time_per_file']}s per file")


def _save_results_to_file(output_json: str) -> str:
    output_dir = '/opt/airflow/output'
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    filename = f'weather_pipeline_results_{timestamp}.json'
    filepath = os.path.join(output_dir, filename)

    with open(filepath, 'w') as f:
        f.write(output_json)
    
    return filepath