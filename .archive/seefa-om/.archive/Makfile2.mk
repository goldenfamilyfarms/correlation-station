.PHONY: help build up down restart logs health clean purge test

# Default target
.DEFAULT_GOAL := help

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

##@ General

help: ## Display this help message
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(GREEN)Observability PoC - Make Commands$(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@awk 'BEGIN {FS = ":.*##"; printf "\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  $(YELLOW)%-15s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(BLUE)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Setup & Deployment

build: ## Build all Docker images
	@echo "$(GREEN)→ Building all Docker images...$(NC)"
	docker-compose build --no-cache
	@echo "$(GREEN)✓ Build complete$(NC)"

up: ## Start all services
	@echo "$(GREEN)→ Starting all services...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✓ All services started$(NC)"
	@echo ""
	@echo "$(BLUE)Service URLs:$(NC)"
	@echo "  Grafana:            http://159.56.4.94:3000"
	@echo "  Correlation Engine: http://159.56.4.94:8080"
	@echo "  Prometheus:         http://159.56.4.94:9090"
	@echo "  Loki:               http://159.56.4.94:3100"
	@echo "  Tempo:              http://159.56.4.94:3200"
	@echo ""
	@echo "$(YELLOW)Run 'make health' to verify all services are healthy$(NC)"

down: ## Stop all services
	@echo "$(RED)→ Stopping all services...$(NC)"
	docker-compose down
	@echo "$(GREEN)✓ All services stopped$(NC)"

restart: down up ## Restart all services

ps: ## List running containers
	@docker-compose ps

##@ Health & Monitoring

health: ## Check health of all services
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(GREEN)Checking Health of All Services$(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@echo ""
	@echo "$(YELLOW)Grafana:$(NC)"
	@curl -sf http://localhost:3000/api/health && echo "$(GREEN)✓ Healthy$(NC)" || echo "$(RED)✗ Unhealthy$(NC)"
	@echo ""
	@echo "$(YELLOW)Loki:$(NC)"
	@curl -sf http://localhost:3100/ready && echo "$(GREEN)✓ Ready$(NC)" || echo "$(RED)✗ Not Ready$(NC)"
	@echo ""
	@echo "$(YELLOW)Tempo:$(NC)"
	@curl -sf http://localhost:3200/ready && echo "$(GREEN)✓ Ready$(NC)" || echo "$(RED)✗ Not Ready$(NC)"
	@echo ""
	@echo "$(YELLOW)Prometheus:$(NC)"
	@curl -sf http://localhost:9090/-/healthy && echo "$(GREEN)✓ Healthy$(NC)" || echo "$(RED)✗ Unhealthy$(NC)"
	@echo ""
	@echo "$(YELLOW)OTel Gateway:$(NC)"
	@curl -sf http://localhost:13133 && echo "$(GREEN)✓ Healthy$(NC)" || echo "$(RED)✗ Unhealthy$(NC)"
	@echo ""
	@echo "$(YELLOW)Correlation Engine:$(NC)"
	@curl -sf http://localhost:8080/health && echo "$(GREEN)✓ Healthy$(NC)" || echo "$(RED)✗ Unhealthy$(NC)"
	@echo ""
	@echo "$(YELLOW)Beorn:$(NC)"
	@curl -sf http://localhost:5001/health && echo "$(GREEN)✓ Healthy$(NC)" || echo "$(RED)✗ Unhealthy$(NC)"
	@echo ""
	@echo "$(YELLOW)Palantir:$(NC)"
	@curl -sf http://localhost:5002/health && echo "$(GREEN)✓ Healthy$(NC)" || echo "$(RED)✗ Unhealthy$(NC)"
	@echo ""
	@echo "$(YELLOW)Arda:$(NC)"
	@curl -sf http://localhost:5003/health && echo "$(GREEN)✓ Healthy$(NC)" || echo "$(RED)✗ Unhealthy$(NC)"
	@echo ""

logs: ## Tail logs from all services
	docker-compose logs -f

logs-engine: ## Tail correlation engine logs
	docker-compose logs -f correlation-engine

logs-gateway: ## Tail OTel gateway logs
	docker-compose logs -f otel-gateway

logs-grafana: ## Tail Grafana logs
	docker-compose logs -f grafana

logs-sense: ## Tail all sense app logs
	docker-compose logs -f beorn palantir arda

##@ Testing

test-logs: ## Send test logs to correlation engine
	@echo "$(GREEN)→ Sending test logs...$(NC)"
	@curl -X POST http://localhost:8080/api/logs \
		-H "Content-Type: application/json" \
		-d '{"resource": {"service": "test", "host": "localhost", "env": "dev"}, "records": [{"timestamp": "'$$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)'", "severity": "INFO", "message": "Test log from Makefile", "labels": {"source": "makefile"}, "trace_id": "12345678901234567890123456789012"}]}'
	@echo ""
	@echo "$(GREEN)✓ Test logs sent$(NC)"

test-trace: ## Generate test traces from sense apps
	@echo "$(GREEN)→ Generating test traces...$(NC)"
	@curl -s http://localhost:5001/api/test | jq '.'
	@curl -s http://localhost:5002/api/test | jq '.'
	@curl -s http://localhost:5003/api/test | jq '.'
	@echo "$(GREEN)✓ Test traces generated$(NC)"

test-traffic: ## Generate test traffic across all services
	@./ops/test-traffic.sh

##@ Metrics & Observability

metrics: ## Show correlation engine metrics
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(GREEN)Correlation Engine Metrics$(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@curl -s http://localhost:8080/metrics | grep -E "^(correlation_|log_records_|traces_received_|export_)" | head -20
	@echo ""

correlations: ## Query recent correlations
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(GREEN)Recent Correlation Events$(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@curl -s "http://localhost:8080/api/correlations?limit=10" | jq '.'

prometheus-query: ## Query Prometheus metrics
	@echo "$(YELLOW)Query:$(NC) correlation_events_total"
	@curl -s 'http://localhost:9090/api/v1/query?query=correlation_events_total' | jq '.data.result'

##@ Cleanup

clean: down ## Stop services and remove volumes
	@echo "$(RED)→ Removing volumes...$(NC)"
	docker-compose down -v
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

purge: clean ## Remove everything including images
	@echo "$(RED)→ Removing images...$(NC)"
	docker-compose down -v --rmi all
	@echo "$(GREEN)✓ Purge complete$(NC)"

prune: ## Remove unused Docker resources
	@echo "$(YELLOW)→ Pruning unused Docker resources...$(NC)"
	docker system prune -f
	@echo "$(GREEN)✓ Prune complete$(NC)"

##@ Development

shell-engine: ## Open shell in correlation engine container
	docker-compose exec correlation-engine /bin/bash

shell-gateway: ## Open shell in OTel gateway container
	docker-compose exec otel-gateway /bin/sh

tail-loki: ## Query recent logs from Loki
	@echo "$(BLUE)Recent logs from Loki:$(NC)"
	@curl -s -G 'http://localhost:3100/loki/api/v1/query' \
		--data-urlencode 'query={service=~".+"}' \
		--data-urlencode 'limit=20' | jq '.data.result[].values[]'

tail-tempo: ## Query recent traces from Tempo
	@echo "$(BLUE)Recent traces from Tempo:$(NC)"
	@curl -s 'http://localhost:3200/api/search?tags=service.name=beorn&limit=10' | jq '.'

##@ Installation (MDSO Alloy)

install-alloy: ## Install Grafana Alloy on MDSO Dev (run on MDSO host)
	@echo "$(YELLOW)→ This should be run on MDSO Dev host (47.43.111.79)$(NC)"
	@echo "Run: cd mdso-alloy && sudo ./install.sh"

##@ Documentation

open-grafana: ## Open Grafana in browser
	@echo "$(GREEN)→ Opening Grafana...$(NC)"
	@open http://159.56.4.94:3000 || xdg-open http://159.56.4.94:3000 || echo "Open: http://159.56.4.94:3000"

open-dashboard: ## Open Correlation Dashboard in Grafana
	@echo "$(GREEN)→ Opening Correlation Dashboard...$(NC)"
	@open http://159.56.4.94:3000/d/correlation-overview || xdg-open http://159.56.4.94:3000/d/correlation-overview

docs: ## Show documentation links
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(GREEN)Documentation$(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@echo ""
	@echo "$(YELLOW)Service URLs:$(NC)"
	@echo "  Grafana:     http://159.56.4.94:3000"
	@echo "  Prometheus:  http://159.56.4.94:9090"
	@echo "  Correlation: http://159.56.4.94:8080"
	@echo ""
	@echo "$(YELLOW)Documentation:$(NC)"
	@echo "  README:    cat README.md"
	@echo "  Runbook:   cat ops/runbook.md"
	@echo "  API Docs:  http://159.56.4.94:8080/docs"
	@echo ""
	@echo "$(YELLOW)Common Commands:$(NC)"
	@echo "  make health     - Check service health"
	@echo "  make logs       - Tail all logs"
	@echo "  make test-trace - Generate test traces"
	@echo "  make metrics    - Show metrics"
	@echo ""

##@ Advanced

backup-dashboards: ## Backup Grafana dashboards
	@mkdir -p backups/dashboards
	@curl -s http://admin:admin@localhost:3000/api/search | jq -r '.[].uid' | \
		while read uid; do \
			echo "Backing up dashboard: $$uid"; \
			curl -s http://admin:admin@localhost:3000/api/dashboards/uid/$$uid | jq '.dashboard' > backups/dashboards/$$uid.json; \
		done
	@echo "$(GREEN)✓ Dashboards backed up to backups/dashboards/$(NC)"

restore-dashboards: ## Restore Grafana dashboards from backup
	@for file in backups/dashboards/*.json; do \
		echo "Restoring dashboard: $$file"; \
		jq -n --argfile dashboard $$file '{dashboard: $$dashboard, overwrite: true}' | \
			curl -X POST http://admin:admin@localhost:3000/api/dashboards/db \
				-H "Content-Type: application/json" \
				-d @-; \
	done
	@echo "$(GREEN)✓ Dashboards restored$(NC)"

check-disk: ## Check disk usage
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(GREEN)Disk Usage$(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@echo ""
	@echo "$(YELLOW)Overall:$(NC)"
	@df -h / | tail -1
	@echo ""
	@echo "$(YELLOW)Docker Volumes:$(NC)"
	@docker system df -v | grep -A 20 "VOLUME NAME"
	@echo ""

check-cardinality: ## Check Loki label cardinality
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(GREEN)Loki Label Cardinality$(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@curl -s http://localhost:3100/loki/api/v1/labels | jq '.'
	@echo ""
	@echo "$(YELLOW)Values per label:$(NC)"
	@for label in $$(curl -s http://localhost:3100/loki/api/v1/labels | jq -r '.data[]'); do \
		echo "$$label: $$(curl -s http://localhost:3100/loki/api/v1/label/$$label/values | jq '.data | length')"; \
	done

stress-test: ## Run stress test
	@echo "$(YELLOW)→ Running stress test...$(NC)"
	@./ops/stress-test.sh

##@ CI/CD

ci-build: ## Build for CI (no cache)
	docker-compose build --no-cache --parallel

ci-test: up ## Run CI tests
	@sleep 30  # Wait for services to be ready
	@make health
	@make test-logs
	@make test-trace
	@echo "$(GREEN)✓ CI tests passed$(NC)"

ci-cleanup: ## Cleanup CI resources
	docker-compose down -v --rmi all
	docker system prune -af