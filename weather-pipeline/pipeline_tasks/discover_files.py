from typing import List
from airflow.decorators import task
from airflow.providers.http.hooks.http import HttpHook

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

        file_list = []

        for year in target_years:
            filename = f"{year}.csv.gz"
            if filename in response.text:
                file_list.append(filename)

        return file_list
    except Exception as e:
        raise Exception(f"Failed to discover files: {str(e)}")