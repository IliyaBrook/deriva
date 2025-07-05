.DEFAULT_GOAL := start
.PHONY: start stop restart logs clean status health dev test

start: ## Start LangGraph service
	@echo "Starting LangGraph service..."
	@docker compose up --build -d
	@echo "🚀 LangGraph service started!"
	@echo "🔗 API: http://localhost:5000"

stop: ## Stop LangGraph service
	@echo "Stopping LangGraph service..."
	@docker compose down
	@echo "🛑 LangGraph service stopped!"

restart: stop start ## Restart LangGraph service

status: ## Show service status
	@docker compose ps

health: ## Check service health
	@echo -n "LangGraph API: "
	@curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/health 2>/dev/null | \
		awk '{if($$1==200) print "✅ Healthy"; else print "❌ Unhealthy"}' || echo "❌ Not accessible"

test: ## Test API endpoint
	@echo "Testing LangGraph API..."
	@sleep 3 2>/dev/null || ping -n 4 127.0.0.1 >nul 2>&1 || timeout /t 3 /nobreak >nul 2>&1 || echo "Waiting..."
	@echo "Testing with length=10:"
	@curl -s -X POST http://localhost:5000/sum_of_squares \
		-H "Content-Type: application/json" \
		-d '{"length": 10}' && \
		echo "" && \
		echo "✅ LangGraph API test successful!" || \
		{ echo "❌ API test failed. Make sure service is running."; exit 1; }

logs: ## Show service logs
	@echo "Showing LangGraph logs (Ctrl+C to exit)..."
	@docker compose logs -f

dev: ## Start in development mode (with logs)
	@echo "Starting LangGraph in development mode..."
	@docker compose up --build

clean: ## Clean environment and volumes
	@echo "Cleaning LangGraph environment..."
	@docker compose down --volumes --remove-orphans
	@echo "✅ LangGraph environment cleaned!" 