from typing import List

from airflow.decorators import task

from utils import (
    get_noaa_client,
    filter_target_years,
    FileDiscoveryError,
    handle_pipeline_error,
)


@task
@handle_pipeline_error(FileDiscoveryError)
def discover_files(**kwargs) -> List[str]:
    dag_run = kwargs.get("dag_run")
    target_years = filter_target_years(dag_run.conf if dag_run else None)

    noaa_client = get_noaa_client()

    response_text = noaa_client.fetch_file_list()

    file_list = []
    for year in target_years:
        filename = f"{year}.csv.gz"
        if filename in response_text:
            file_list.append(filename)

    return file_list
