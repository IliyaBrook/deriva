import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List


class ProcessingConstants:
    CHUNK_SIZE = 1000000
    MAX_STATIONS_PER_CHUNK = 1000
    MAX_UNIQUE_STATIONS = 100000
    GARBAGE_COLLECTION_INTERVAL = 3

    TEMPERATURE_VALIDATION_RANGE = (-100, 100)
    TEMPERATURE_CONVERSION_FACTOR = 10.0

    MEASUREMENT_TYPES = ["TMAX", "TMIN", "PRCP"]

    CSV_COLUMNS = [
        "ID",
        "DATE",
        "ELEMENT",
        "VALUE",
        "MFLAG",
        "QFLAG",
        "SFLAG",
        "OBSTIME",
    ]
    CSV_DTYPES = {"ID": "str", "DATE": "str", "ELEMENT": "str", "VALUE": "float64"}


class ProcessingState:
    def __init__(self):
        self.phase = "initialization"
        self.progress_percent = 0
        self.current_chunk = 0
        self.total_chunks_estimated = 0
        self.start_time = time.time()

    def update_phase(self, phase: str, progress: int = None):
        self.phase = phase
        if progress is not None:
            self.progress_percent = progress

    def update_progress(self, current_chunk: int, total_chunks: int = None):
        self.current_chunk = current_chunk
        if total_chunks:
            self.total_chunks_estimated = total_chunks
            progress = min(90, 10 + (current_chunk / max(1, total_chunks)) * 80)
            self.progress_percent = int(progress)

    def get_elapsed_time(self) -> float:
        return time.time() - self.start_time

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase": self.phase,
            "progress_percent": self.progress_percent,
            "current_chunk": self.current_chunk,
            "total_chunks_estimated": self.total_chunks_estimated,
        }


def get_current_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def format_file_processing_result(
    filename: str,
    total_records: int,
    unique_stations: int,
    date_range: Dict[str, str],
    measurement_counts: Dict[str, int],
    temperature_stats: Dict[str, float],
    processing_seconds: float,
    processing_state: Optional[ProcessingState] = None,
) -> Dict[str, Any]:
    result = {
        "file_name": filename,
        "processed_at": get_current_timestamp(),
        "total_records": int(total_records),
        "unique_stations": int(unique_stations),
        "date_range": date_range,
        "measurement_counts": {k: int(v) for k, v in measurement_counts.items()},
        "temperature_stats": temperature_stats,
        "processing_seconds": round(processing_seconds, 2),
    }

    if processing_state:
        result["processing_state"] = processing_state.to_dict()

    return result


def format_error_result(
    filename: str,
    error: Exception,
    processing_seconds: float,
    processing_state: Optional[ProcessingState] = None,
) -> Dict[str, Any]:
    result = {
        "file_name": filename,
        "processed_at": get_current_timestamp(),
        "error": str(error),
        "error_type": type(error).__name__,
        "processing_seconds": round(processing_seconds, 2),
        "status": "failed",
    }

    if processing_state:
        state_dict = processing_state.to_dict()
        result["processing_state"] = {
            k: int(v) if isinstance(v, (int, float)) and k != "phase" else v
            for k, v in state_dict.items()
        }

    return result


def calculate_progress_percentage(
    current: int, total: int, base: int = 10, max_progress: int = 90
) -> int:
    if total <= 0:
        return base
    return min(max_progress, base + (current / total) * (max_progress - base))


def should_run_garbage_collection(chunk_number: int, interval: int = None) -> bool:
    interval = interval or ProcessingConstants.GARBAGE_COLLECTION_INTERVAL
    return chunk_number % interval == 0


def filter_target_years(
    dag_run_conf: Optional[Dict], default_years: List[str] = None
) -> List[str]:
    default_years = default_years or ["2020", "2021", "2022", "2023"]

    if dag_run_conf:
        return dag_run_conf.get("years", default_years)
    return default_years


def log_processing_metrics(
    filename: str,
    total_records: int,
    unique_stations: int,
    temperature_stats: Dict[str, float],
    processing_time: float,
):
    print(f"🎉 Successfully processed {filename} in {processing_time:.1f}s!")
    print(f"📊 Final stats: {total_records:,} records, {unique_stations:,} stations")
    print(
        f"🌡️  Temperatures: TMAX avg {temperature_stats['avg_max_c']}°C, TMIN avg {temperature_stats['avg_min_c']}°C"
    )


def log_download_metrics(filename: str, download_time: float, file_size_bytes: int):
    file_size_mb = file_size_bytes / (1024 * 1024)
    print(f"📥 Downloaded {filename} in {download_time:.1f}s")
    print(f"📊 File size: {file_size_mb:.1f} MB ({file_size_bytes:,} bytes)")


def log_chunk_progress(chunk_number: int, chunk_size: int, progress_percent: int):
    print(
        f"📊 Chunk {chunk_number}: {chunk_size:,} records | Progress: {progress_percent}%"
    )


def log_error_details(
    filename: str, error: Exception, processing_state: ProcessingState
):
    print(
        f"❌ Failed to process {filename} in phase '{processing_state.phase}': {str(error)}"
    )
    print(
        f"🔍 Error details: {type(error).__name__} at {processing_state.progress_percent}% completion"
    )
