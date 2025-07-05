from typing import Any, Callable, Optional
import functools


class PipelineError(Exception):
    def __init__(self, message: str, phase: str = None, filename: str = None):
        self.message = message
        self.phase = phase
        self.filename = filename
        super().__init__(self.message)


class FileDiscoveryError(PipelineError):
    def __init__(self, message: str, filename: str = None):
        super().__init__(message, phase='file_discovery', filename=filename)


class FileProcessingError(PipelineError):
    def __init__(self, message: str, filename: str = None, phase: str = None):
        super().__init__(message, phase=phase or 'file_processing', filename=filename)


class ConsolidationError(PipelineError):
    def __init__(self, message: str):
        super().__init__(message, phase='consolidation')


def handle_pipeline_error(error_type: type = PipelineError, phase: str = None, filename: str = None):
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if isinstance(e, PipelineError):
                    raise
                
                error_msg = f"Failed in {func.__name__}: {str(e)}"
                raise error_type(error_msg, phase=phase, filename=filename) from e
        return wrapper
    return decorator


def safe_execute(func: Callable, *args, default_value: Any = None, log_errors: bool = True, **kwargs) -> Any:
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_errors:
            print(f"⚠️ Warning in {func.__name__}: {str(e)}")
        return default_value


def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        print(f"⚠️ Attempt {attempt + 1} failed for {func.__name__}: {str(e)}")
                        print(f"🔄 Retrying in {current_delay:.1f}s...")
                        import time
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        print(f"❌ All {max_retries + 1} attempts failed for {func.__name__}")
                        
            raise last_exception
        return wrapper
    return decorator 