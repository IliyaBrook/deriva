# Weather Data Pipeline - Apache Airflow ETL

Apache Airflow ETL pipeline for processing NOAA weather data from 2020-2023.

**Part of Deriva.ai Take-Home Assignment - Task 1**

## Features

- **Apache Airflow 2.5.3**: Production-ready ETL orchestration
- **HTTPHook Integration**: All remote calls use Apache Airflow HTTPHook
- **Dynamic Task Mapping**: Parallel processing of weather data files
- **Authentication Enabled**: Secure access with admin credentials
- **Fault Tolerant**: Automatic retries and error handling
- **Idempotent**: Safe to run multiple times
- **Docker Compose**: One-command startup with `docker compose up`

## Architecture

The pipeline consists of three main components:

1. **File Discovery**: HTTPHook to list and filter NOAA data files (2020-2023)
2. **Parallel Processing**: Dynamic Task Mapping for concurrent download/processing
3. **Results Consolidation**: JSON output with standardized schema

## Quick Start

### Using Makefile (Recommended)

```bash
make init     # Initialize Airflow database
make start    # Start all services
make run-dag  # Trigger weather data pipeline DAG
```

### Manual Setup

1. **Create Environment File**
   Create `.env` file with required variables:
   ```bash
   # Required environment variables for weather-pipeline/.env
   AIRFLOW_UID=50000
   AIRFLOW__CORE__FERNET_KEY=your_fernet_key_here_generate_with_python_cryptography_fernet
   AIRFLOW__CORE__MAX_ACTIVE_RUNS_PER_DAG=4
   AIRFLOW__CORE__PARALLELISM=4
   AIRFLOW_ADMIN_USERNAME=admin
   AIRFLOW_ADMIN_PASSWORD=admin123
   AIRFLOW_ADMIN_FIRSTNAME=Admin
   AIRFLOW_ADMIN_LASTNAME=User
   AIRFLOW_ADMIN_EMAIL=admin@example.com
   POSTGRES_DB=airflow
   POSTGRES_USER=airflow
   POSTGRES_PASSWORD=airflow
   ```

2. **Build Custom Image**
   ```bash
   docker compose build
   ```

3. **Initialize Database**
   ```bash
   docker compose up airflow-init
   ```

4. **Start All Services**
   ```bash
   docker compose up
   ```

### Access

- **Airflow WebUI**: http://localhost:8080
- **Authentication**: Enabled (see .env for credentials)
- **Default Login**: admin/admin123 (configurable in .env)

## Makefile Commands

| Command | Description |
|---------|-------------|
| `make build` | Build custom Airflow image |
| `make init` | Initialize Airflow database |
| `make start` | Start Airflow services |
| `make stop` | Stop Airflow services |
| `make restart` | Restart Airflow services |
| `make reset`   | Fully rebuilds the environment (clean + init + start) |
| `make status` | Show service status |
| `make health` | Check service health |
| `make logs` | Show Airflow logs |
| `make run-dag` | Trigger weather data pipeline DAG |
| `make cli` | Access Airflow CLI |
| `make clean` | Clean environment and volumes |

## Usage

### Web Interface

1. Navigate to http://localhost:8080
2. Enable the `weather_data_pipeline` DAG
3. Trigger the DAG manually
4. Monitor execution in the Graph View

### REST API

#### Check DAG Status
```bash
# Get all DAGs
curl -X GET "http://localhost:8080/api/v1/dags"

# Get specific DAG
curl -X GET "http://localhost:8080/api/v1/dags/weather_data_pipeline"
```

#### Trigger Pipeline
```bash
# Default execution (years 2020-2023)
curl -X POST "http://localhost:8080/api/v1/dags/weather_data_pipeline/dagRuns" \
  -H "Content-Type: application/json" \
  -d '{
    "conf": {}
  }'

# Custom years execution
curl -X POST "http://localhost:8080/api/v1/dags/weather_data_pipeline/dagRuns" \
  -H "Content-Type: application/json" \
  -d '{
    "conf": {
      "years": ["2021", "2022"]
    }
  }'
```

#### Monitor Execution
```bash
# Get all DAG runs
curl -X GET "http://localhost:8080/api/v1/dags/weather_data_pipeline/dagRuns"

# Get specific DAG run
curl -X GET "http://localhost:8080/api/v1/dags/weather_data_pipeline/dagRuns/{dag_run_id}"

# Get task instances for a run
curl -X GET "http://localhost:8080/api/v1/dags/weather_data_pipeline/dagRuns/{dag_run_id}/taskInstances"
```

#### Get Results
```bash
# Get task logs
curl -X GET "http://localhost:8080/api/v1/dags/weather_data_pipeline/dagRuns/{dag_run_id}/taskInstances/{task_id}/logs/1"

# Get XCom data (task outputs)
curl -X GET "http://localhost:8080/api/v1/dags/weather_data_pipeline/dagRuns/{dag_run_id}/taskInstances/{task_id}/xcomEntries"
```

### Postman Collection

#### 1. Trigger Pipeline
- **Method**: POST
- **URL**: `http://localhost:8080/api/v1/dags/weather_data_pipeline/dagRuns`
- **Headers**: `Content-Type: application/json`
- **Body (Default years)**:
```json
{
  "conf": {}
}
```

- **Body (Custom years)**:
```json
{
  "conf": {
    "years": ["2021", "2022", "2023"]
  }
}
```

#### 2. Check DAG Status
- **Method**: GET
- **URL**: `http://localhost:8080/api/v1/dags/weather_data_pipeline`

#### 3. Monitor Runs
- **Method**: GET
- **URL**: `http://localhost:8080/api/v1/dags/weather_data_pipeline/dagRuns`

#### 4. Get Task Details
- **Method**: GET
- **URL**: `http://localhost:8080/api/v1/dags/weather_data_pipeline/dagRuns/{dag_run_id}/taskInstances`

### Complete API Workflow

#### Step-by-Step Pipeline Execution

**1. Verify DAG is Available**
```bash
curl -X GET "http://localhost:8080/api/v1/dags/weather_data_pipeline"
```

**2. Trigger Pipeline** (default years)
```bash
curl -X POST "http://localhost:8080/api/v1/dags/weather_data_pipeline/dagRuns" \
  -H "Content-Type: application/json" \
  -d '{"conf": {}}'
```

**2b. Trigger Pipeline** (custom years)
```bash
curl -X POST "http://localhost:8080/api/v1/dags/weather_data_pipeline/dagRuns" \
  -H "Content-Type: application/json" \
  -d '{"conf": {"years": ["2020", "2021"]}}'
```

**3. Get DAG Run ID** (from step 2 response)
```json
{
  "dag_run_id": "manual__2024-01-15T10:30:00+00:00"
}
```

**4. Monitor Progress**
```bash
# Check run status
curl -X GET "http://localhost:8080/api/v1/dags/weather_data_pipeline/dagRuns/manual__2024-01-15T10:30:00+00:00"

# Check task instances
curl -X GET "http://localhost:8080/api/v1/dags/weather_data_pipeline/dagRuns/manual__2024-01-15T10:30:00+00:00/taskInstances"
```

**5. Get Results**
```bash
# Get consolidation task output
curl -X GET "http://localhost:8080/api/v1/dags/weather_data_pipeline/dagRuns/manual__2024-01-15T10:30:00+00:00/taskInstances/consolidate_results/xcomEntries"

# Get processing logs
curl -X GET "http://localhost:8080/api/v1/dags/weather_data_pipeline/dagRuns/manual__2024-01-15T10:30:00+00:00/taskInstances/consolidate_results/logs/1"
```

#### PowerShell Examples (Windows)

**Trigger Pipeline** (default):
```powershell
$headers = @{ "Content-Type" = "application/json" }
$body = @{ conf = @{} } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8080/api/v1/dags/weather_data_pipeline/dagRuns" -Method POST -Headers $headers -Body $body
```

**Trigger Pipeline** (custom years):
```powershell
$headers = @{ "Content-Type" = "application/json" }
$body = @{ 
    conf = @{ years = @("2021", "2022") } 
} | ConvertTo-Json -Depth 3
Invoke-RestMethod -Uri "http://localhost:8080/api/v1/dags/weather_data_pipeline/dagRuns" -Method POST -Headers $headers -Body $body
```

**Check Status**:
```powershell
Invoke-RestMethod -Uri "http://localhost:8080/api/v1/dags/weather_data_pipeline/dagRuns" -Method GET
```

### API Response Examples

#### Successful DAG Trigger
```json
{
  "dag_id": "weather_data_pipeline",
  "dag_run_id": "manual__2024-01-15T10:30:00+00:00",
  "logical_date": "2024-01-15T10:30:00+00:00",
  "execution_date": "2024-01-15T10:30:00+00:00",
  "start_date": null,
  "end_date": null,
  "state": "queued",
  "conf": {}
}
```

#### DAG Run Status
```json
{
  "dag_runs": [
    {
      "dag_id": "weather_data_pipeline",
      "dag_run_id": "manual__2024-01-15T10:30:00+00:00",
      "state": "success",
      "start_date": "2024-01-15T10:30:00+00:00",
      "end_date": "2024-01-15T10:32:45+00:00",
      "conf": {}
    }
  ]
}
```

### Troubleshooting API

#### Common Issues

**1. DAG Not Found**
```json
{"detail": "DAG with dag_id: 'weather_data_pipeline' not found"}
```
**Solutions**:
```bash
# Check if DAG is loaded
curl -X GET "http://localhost:8080/api/v1/dags"

# Check DAG file syntax
docker compose exec airflow-scheduler python -m py_compile /opt/airflow/dags/weather_data_pipeline.py

# Check scheduler logs
docker compose logs airflow-scheduler --tail=50

# Force DAG refresh (if needed)
docker compose restart airflow-scheduler
```

**2. Invalid Request Body**
```json
{"detail": "logical_date is required"}
```
**Solution**: Include required fields in POST body:
```json
{
  "logical_date": null,
  "conf": {}
}
```

**3. Authentication Required**
```json
{"detail": "Unauthorized"}
```
**Solution**: Check authentication settings in docker-compose.yml:
```yaml
AIRFLOW__WEBSERVER__AUTHENTICATE: "false"
AIRFLOW__WEBSERVER__RBAC: "false"
```

**4. DAG Import Errors**
Check for Python import issues:
```bash
# Test DAG import
docker compose exec airflow-scheduler python -c "
import sys
sys.path.append('/opt/airflow/dags')
from weather_data_pipeline import dag
print('DAG imported successfully:', dag.dag_id)
"
```

#### Health Checks

**Service Status**:
```bash
# Check all services
docker compose ps

# Check Airflow health
curl -X GET "http://localhost:8080/health"

# Check API version
curl -X GET "http://localhost:8080/api/v1/version"
```

**DAG Validation**:
```bash
# List all available DAGs
curl -X GET "http://localhost:8080/api/v1/dags" | jq '.dags[] | {dag_id, is_active, is_paused}'

# Check DAG details
curl -X GET "http://localhost:8080/api/v1/dags/weather_data_pipeline" | jq '.'
```

### Pipeline Output

The pipeline generates JSON output with the following schema for each file:

```json
{
  "file_name": "2020.csv.gz",
  "processed_at": "2024-01-15T10:30:00.000Z",
  "total_records": 1234567,
  "unique_stations": 5678,
  "date_range": {
    "start": "2020-01-01",
    "end": "2020-12-31"
  },
  "measurement_counts": {
    "TMAX": 456789,
    "TMIN": 456789,
    "PRCP": 321456
  },
  "temperature_stats": {
    "avg_max_c": 15.2,
    "avg_min_c": 5.8
  },
  "processing_seconds": 45.67
}
```

## Data Source

- **Source**: https://www.ncei.noaa.gov/pub/data/ghcn/daily/by_year/
- **Files**: 2020.csv.gz, 2021.csv.gz, 2022.csv.gz, 2023.csv.gz
- **Format**: Global Historical Climatology Network Daily (GHCN-D)

## Technical Details

### Components

- **Apache Airflow 2.5.3**: Workflow orchestration (webserver + scheduler)
- **PostgreSQL 13**: Metadata database
- **Python 3.8+**: Pipeline logic
- **Pandas**: Data processing
- **HTTPHook**: NOAA API integration

### Key Features

- **Idempotent Processing**: Safe to rerun
- **Error Handling**: Automatic retries with exponential backoff
- **Parallel Execution**: Dynamic task mapping for performance
- **Comprehensive Logging**: Full audit trail
- **Health Checks**: Service monitoring

## Configuration

### Pipeline Parameters

The pipeline supports configurable years through DAG `conf`:

**Default behavior** (meets requirements):
- Years: 2020, 2021, 2022, 2023
- No configuration needed

**Custom years** (for flexibility):
```json
{
  "conf": {
    "years": ["2021", "2022"]
  }
}
```

### HTTP Connection

The pipeline uses a predefined HTTP connection:
- **Connection ID**: `noaa_http_default`
- **Host**: `www.ncei.noaa.gov`
- **Type**: HTTP

### Environment Variables

- `AIRFLOW_UID`: User ID for file permissions
- `AIRFLOW__WEBSERVER__AUTHENTICATE`: Disabled authentication (set to "false")
- `AIRFLOW__WEBSERVER__RBAC`: Disabled RBAC (set to "false")

## Troubleshooting

### Common Issues

1. **Permission Errors**
   ```bash
   sudo chown -R $USER:$USER ./dags ./logs ./plugins
   ```

2. **Memory Issues**
   - Ensure 4GB+ RAM available
   - Close other Docker containers

3. **Port Conflicts**
   - Change port in docker-compose.yml if 8080 is in use

### Cleanup

```bash
docker compose down --volumes --remove-orphans
```

## Development

### Adding New Tasks

1. Edit `dags/weather_data_pipeline.py`
2. Follow Airflow TaskFlow API patterns
3. Restart containers to reload DAG

### Custom Connections

Add connections via Airflow WebUI:
Admin → Connections → Create

## Monitoring

### Key Metrics

- **Processing Time**: Per-file processing duration
- **Data Quality**: Record counts and validation
- **Success Rate**: Task completion percentage
- **Resource Usage**: Memory and CPU utilization

### Logs

- **Location**: `./logs/`
- **Format**: Structured JSON logging
- **Retention**: Configurable via Airflow settings 