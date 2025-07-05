from datetime import datetime, timedelta

from airflow import DAG

from pipeline_tasks.consolidate_results import consolidate_results
from pipeline_tasks.discover_files import discover_files
from pipeline_tasks.process_file import process_file

default_args = {
    'owner': 'deriva',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

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

    # noinspection PyStatementEffect,PyUnresolvedReferences
    files >> processed_results >> final_output