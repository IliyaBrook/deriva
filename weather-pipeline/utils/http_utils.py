from airflow.providers.http.hooks.http import HttpHook
from typing import Optional, Dict, Any


class NOAAHttpClient:
    DEFAULT_CONN_ID = 'noaa_http_default'
    BASE_ENDPOINT = 'pub/data/ghcn/daily/by_year/'
    DEFAULT_TIMEOUT = 1800
    
    def __init__(self, conn_id: str = None, timeout: int = None):
        self.conn_id = conn_id or self.DEFAULT_CONN_ID
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        self._hook = None
    
    def get_hook(self) -> HttpHook:
        if self._hook is None:
            self._hook = HttpHook(method='GET', http_conn_id=self.conn_id)
        return self._hook
    
    def fetch_file_list(self, headers: Optional[Dict[str, str]] = None) -> str:
        hook = self.get_hook()
        response = hook.run(
            endpoint=self.BASE_ENDPOINT,
            headers=headers or {'Accept': 'text/html'}
        )
        return response.text
    
    def download_file(self, filename: str, stream: bool = True) -> Any:
        hook = self.get_hook()
        endpoint = f"{self.BASE_ENDPOINT}{filename}"
        
        extra_options = {'timeout': self.timeout}
        if stream:
            extra_options['stream'] = True
            
        return hook.run(endpoint=endpoint, extra_options=extra_options)


def get_noaa_client(conn_id: str = None, timeout: int = None) -> NOAAHttpClient:
    return NOAAHttpClient(conn_id, timeout) 