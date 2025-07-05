.DEFAULT_GOAL := start
.PHONY: build init start stop restart logs clean status health run-dag

build: ## Build custom Airflow image
	@echo "Building custom Airflow image..."
	@docker compose build
	@echo "🏗️ Custom image built successfully!"

init: ## Initialize Airflow database
	@echo "Initializing Airflow database and creating admin user..."
	@docker compose up airflow-init
	@echo "✅ Airflow database initialized and admin user created!"
	@echo "📊 WebUI will be available at: http://localhost:8080"
	@echo "🔑 Login credentials: see .env file (AIRFLOW_ADMIN_USERNAME/AIRFLOW_ADMIN_PASSWORD)"

start: ## Start Airflow services
	@echo "Starting Airflow services..."
	@docker compose up -d
	@echo "🚀 Airflow services started!"
	@echo "📊 WebUI: http://localhost:8080 (airflow/airflow)"

stop: ## Stop Airflow services
	@echo "Stopping Airflow services..."
	@docker compose down
	@echo "🛑 Airflow services stopped!"

restart: stop start ## Restart Airflow services

reset: clean init start ## Fully rebuilds the environment (clean + init + start)

status: ## Show service status
	@docker compose ps

health: ## Check service health
	@echo -n "Airflow WebUI: "
	@curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health 2>/dev/null | \
		awk '{if($$1==200) print "✅ Healthy"; else print "❌ Unhealthy"}' || echo "❌ Not accessible"

logs: ## Show Airflow logs
	@echo "Showing Airflow logs (Ctrl+C to exit)..."
	@docker compose logs -f

run-dag: ## Trigger weather data pipeline DAG
	@echo "Triggering weather data pipeline DAG..."
	@sleep 3 2>/dev/null || ping -n 4 127.0.0.1 >nul 2>&1 || timeout /t 3 /nobreak >nul 2>&1 || echo "Waiting..."
	@echo "Triggering DAG via REST API (with Basic Auth):"
	@curl -s -X POST http://localhost:8080/api/v1/dags/weather_data_pipeline/dagRuns \
		-u airflow:airflow \
		-H "Content-Type: application/json" \
		-d '{"conf": {}}' && \
		echo "" && \
		echo "✅ Weather data pipeline DAG triggered successfully!" || \
		{ echo "❌ Failed to trigger DAG. Check credentials or service status."; exit 1; }

clean: ## Clean environment and volumes
	@echo "Cleaning Airflow environment..."
	@docker compose down --volumes --remove-orphans
	@echo "✅ Airflow environment cleaned!" 