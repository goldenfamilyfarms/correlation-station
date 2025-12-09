.PHONY: help build up down logs restart test

help:
	@echo "Correlation API - Build & Run"
	@echo ""
	@echo "Commands:"
	@echo "  make build    - Build Docker image (requires ARTIFACTORY credentials in .env)"
	@echo "  make up       - Start container"
	@echo "  make down     - Stop container"
	@echo "  make restart  - Restart container"
	@echo "  make logs     - View logs"
	@echo "  make test     - Test API endpoints"
	@echo ""
	@echo "Note: Set ARTIFACTORY_USER and ARTIFACTORY_TOKEN in parent .env file"

build:
	@echo "Building Correlation API..."
	@if [ -z "$(shell grep ARTIFACTORY_USER ../.env 2>/dev/null)" ]; then \
		echo "ERROR: ARTIFACTORY_USER not set in .env"; \
		echo "Add to .env: ARTIFACTORY_USER=your.name@charter.com"; \
		exit 1; \
	fi
	docker compose build

up:
	@echo "Starting Correlation API..."
	docker compose up -d
	@sleep 3
	@echo "✓ API running at http://localhost:8080"
	@echo "  Docs: http://localhost:8080/docs"

down:
	@echo "Stopping Correlation API..."
	docker compose down

restart: down build up
	@echo "✓ API restarted"

logs:
	docker compose logs -f

test:
	@echo "Testing Correlation API..."
	@echo ""
	@echo "1. Health check:"
	@curl -s http://localhost:8080/health | jq '.' || echo "API not responding"
	@echo ""
	@echo "2. Stats:"
	@curl -s http://localhost:8080/stats | jq '.' || echo "API not responding"
	@echo ""
	@echo "3. Test ingest (requires auth token from .env):"
	@curl -s -X POST http://localhost:8080/ingest \
		-H "Authorization: Bearer $$(grep CORRELATION_API_AUTH_TOKEN ../.env | cut -d= -f2)" \
		-H "Content-Type: application/json" \
		-d '{"resourceSpans":[]}' | jq '.'