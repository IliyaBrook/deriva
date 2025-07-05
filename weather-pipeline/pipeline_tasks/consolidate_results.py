import json
from datetime import datetime, timezone
from typing import List, Dict, Any

from airflow.decorators import task


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
    # noinspection PyTypeChecker
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