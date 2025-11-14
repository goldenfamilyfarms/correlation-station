.PHONY: help build up down logs restart test clean

help:
	@echo "Correlation Engine Enhanced - Build & Run"
	@echo ""
	@echo "Commands:"
	@echo "  make build    - Build Docker image"
	@echo "  make up       - Start container"
	@echo "  make down     - Stop container"
	@echo "  make restart  - Restart container"
	@echo "  make logs     - View logs"
	@echo "  make test     - Test API endpoints"
	@echo "  make clean    - Clean up containers and images"

build:
	@echo "Building Correlation Engine Enhanced..."
	docker compose build

up:
	@echo "Starting Correlation Engine Enhanced..."
	docker compose up -d
	@sleep 3
	@echo "✓ API running at http://localhost:8080"
	@echo "  Docs: http://localhost:8080/docs"
	@echo "  Health: http://localhost:8080/health"
	@echo "  MDSO Status: http://localhost:8080/api/mdso/status"

down:
	@echo "Stopping Correlation Engine Enhanced..."
	docker compose down

restart: down build up
	@echo "✓ API restarted"

logs:
	docker compose logs -f

test:
	@echo "Testing Correlation Engine Enhanced..."
	@echo ""
	@echo "1. Health check:"
	@curl -s http://localhost:8080/health | jq '.' || echo "API not responding"
	@echo ""
	@echo "2. MDSO Status:"
	@curl -s http://localhost:8080/api/mdso/status | jq '.' || echo "API not responding"
	@echo ""
	@echo "3. MDSO Products:"
	@curl -s http://localhost:8080/api/mdso/products | jq '.' || echo "API not responding"

clean:
	@echo "Cleaning up..."
	docker compose down -v
	docker rmi correlation-engine-enhanced 2>/dev/null || true
	@echo "✓ Cleanup complete"
