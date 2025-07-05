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

1. **Create Environment File**
   Create `.env` file with required variables:
   ```bash
   AIRFLOW_UID=50000

   POSTGRES_USER=airflow
   POSTGRES_PASSWORD=airflow
   POSTGRES_DB=airflow

   AIRFLOW_ADMIN_USERNAME=airflow
   AIRFLOW_ADMIN_PASSWORD=airflow
   AIRFLOW_ADMIN_FIRSTNAME=Admin
   AIRFLOW_ADMIN_LASTNAME=User
   AIRFLOW_ADMIN_EMAIL=example@email.com

   AIRFLOW__CORE__FERNET_KEY=qBXKGKVUlnNDAB6FLV-yMBTwIomZZzYxI8vwLNgNJ6Y=
   ```

### Access

- **Airflow WebUI**: http://localhost:8080
- **Authentication**: Enabled (see .env for credentials)
- **Default Login**: example admin/admin123 (configurable in .env)

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
| `make clean` | Clean environment and volumes |

## Usage

### Web Interface

1. Navigate to http://localhost:8080
2. Enable the `weather_data_pipeline` DAG
   or use `make run-dag` command
3. Trigger the DAG manually
4. Monitor execution in the Graph View
5. TAfter the DAG completes, you will see a .json file locally in the weather-pipeline\output folder.

### REST API

#### Check DAG Status
```bash
# Get all DAGs Info
curl -X GET "http://localhost:8080/api/v1/dags"

# Get specific DAG Info
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