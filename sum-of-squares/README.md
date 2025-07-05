# Sum of Squares API - LangGraph Map-Reduce

LangGraph-powered Map-Reduce service for calculating sum-of-squares from random integers.

**Part of Deriva.ai Take-Home Assignment - Task 2**

## Features

- **LangGraph Integration**: Modern graph-based workflow orchestration
- **Send API**: Parallel mapper execution using LangGraph Send API
- **Map-Reduce Pattern**: Generator → Parallel Mappers → Reducer
- **Flask API**: RESTful endpoint for sum of squares calculation
- **Docker Compose**: One-command startup
- **Error Handling**: Comprehensive input validation and error responses

## Architecture

### Graph Design

1. **Generator Node**: Produces list of random integers (0-99)
2. **Mapper Branch**: Squares each number in **parallel** using Send API
3. **Reducer Node**: Sums all squared results and returns JSON

### LangGraph Send API

The project demonstrates fan-out/fan-in parallel execution:

```python
def assign_mappers(state: State) -> List[Send]:
    numbers = state["numbers"]
    return [Send("mapper", {"number": num}) for num in numbers]
```

## Quick Start

### Using Makefile (Recommended)

```bash
make start    # Start service
make test     # Test API endpoint
```

### Manual Setup

1. **Start Service**
   ```bash
   docker compose up --build
   ```

2. **Verify Service**
   ```bash
   curl http://localhost:5000/health
   ```

## Makefile Commands

| Command | Description |
|---------|-------------|
| `make start` | Start LangGraph service |
| `make stop` | Stop LangGraph service |
| `make restart` | Restart LangGraph service |
| `make status` | Show service status |
| `make health` | Check service health |
| `make test` | Test API endpoint |
| `make logs` | Show service logs |
| `make clean` | Clean environment and volumes |

## API Usage

### Endpoint

```
POST /sum_of_squares
Content-Type: application/json
```

### Request Format

```json
{
  "length": 100
}
```

### Response Format

```json
{
  "sum_of_squares": 123456
}
```

### Example Usage

```bash
curl -X POST http://localhost:5000/sum_of_squares \
  -H "Content-Type: application/json" \
  -d '{"length": 100}'
```

### Expected Response

```json
{
  "sum_of_squares": 328350
}
```

## Validation

### Input Constraints

- **length**: Must be positive integer
- **Maximum**: 10,000 (performance limit)
- **Minimum**: 1

### Error Responses

```json
{
  "error": "Length must be a positive integer"
}
```

## Technical Implementation

### State Management

```python
class State(TypedDict):
    length: int
    numbers: List[int]
    squared_results: Annotated[List[int], operator.add]
    sum_of_squares: int
```

### Parallel Execution

The `Send` API enables concurrent processing:

- **Fan-out**: Each number gets its own mapper task
- **Parallel Processing**: All mappers execute simultaneously
- **Fan-in**: Results aggregate automatically via reducer

### Graph Flow

```
START → Generator → [Mapper, Mapper, ...] → Reducer → END
```

## LangGraph Studio Recording

For demonstration of fan-out/fan-in execution:

1. Open LangGraph Studio
2. Load `graphs/main_graph.py`
3. Execute with `{"length": 10}`
4. Observe parallel mapper execution
5. Record 60-90 second demonstration

## Development

### Local Testing

```bash
python graphs/main_graph.py
```

### Manual Verification

The graph includes built-in verification:

```python
manual_check = sum(num ** 2 for num in result['numbers'])
print(f"Results match: {result['sum_of_squares'] == manual_check}")
```

### Adding Features

1. Edit `graphs/main_graph.py` for graph logic
2. Modify `app.py` for API endpoints
3. Update `requirements.txt` for dependencies
4. Rebuild with `docker compose up --build`

### Docker Settings

- **Image**: Python 3.11 slim
- **Ports**: 5000:5000
- **Health Check**: `/health` endpoint
- **Restart Policy**: unless-stopped

## Monitoring

```bash
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "sum-of-squares"
}
```

### Logging

- **Location**: Docker container logs
- **Format**: Structured JSON
- **Level**: INFO (configurable)

### Metrics

- **Request Count**: Per endpoint
- **Response Time**: Average processing time
- **Error Rate**: Failed requests percentage
- **Parallel Tasks**: Active mapper count


## Testing

### Unit Tests

```bash
python -m pytest tests/
```

### Test

```bash
curl -X POST http://localhost:5000/sum_of_squares \
  -H "Content-Type: application/json" \
  -d '{"length": 5}'
```

## Cleanup

```bash
docker compose down --volumes
``` 