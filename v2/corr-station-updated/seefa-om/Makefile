# ============================================
# Observability PoC - Makefile
# ============================================
# Author: derrick.golden@chater.com
# Purpose: Orchestrate observability stack deployment
# ============================================

# Shell configuration
SHELL := /bin/bash
.SHELLFLAGS := -euo pipefail -c

# Default target
.DEFAULT_GOAL := help

# Prevent make from printing directory changes
MAKEFLAGS += --no-print-directory

# ============================================
# Variables
# ============================================

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

# Include environment variables if .env exists
-include .env
export

# Docker compose command (auto-detect v1 vs v2)
DOCKER_COMPOSE := $(shell which docker-compose >/dev/null 2>&1 && echo "docker-compose" || echo "docker compose")

# Service directories
STACK_DIR := observability-stack
GATEWAY_DIR := gateway
CORR_DIR := correlation-engine
SENSE_DIR := sense-apps

# Common paths
OM_DIR := /opt/correlation-station/seefa-om
SENSE_TEST_DIR := /opt/correlation-station/sense-test
NGINX_CONF_DIR := /etc/nginx/conf.d

# Timestamp for backups
TIMESTAMP := $(shell date +%Y%m%d_%H%M%S)

# ============================================
# Help Target
# ============================================
.PHONY: help
help: ## Show this help message
	@printf "$(BLUE)========================================$(NC)\n"
	@printf "$(GREEN)Observability PoC - Make Commands$(NC)\n"
	@printf "$(BLUE)========================================$(NC)\n"
	@awk 'BEGIN {FS = ":.*##"; printf "\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(BLUE)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(BLUE)Quick Start:$(NC)"
	@echo "  1. make pre-setup      # Run pre-setup checks (FIRST TIME ONLY)"
	@echo "  2. make start-all      # Start all services"
	@echo "  3. make health         # Verify all services"
	@echo "  4. make test-trace     # Generate test telemetry"
	@echo ""
	@echo "$(BLUE)Common Operations:$(NC)"
	@echo "  make status            # Show all service status"
	@echo "  make logs              # Tail all logs"
	@echo "  make logs-<service>    # Tail specific service logs"
	@echo "  make stop-all          # Stop all services"
	@echo "  make restart           # Restart all services"
	@echo ""
	@echo "$(BLUE)Service URLs:$(NC)"
	@echo "  Grafana:     http://159.56.4.94:8443"
	@echo "  Prometheus:  http://159.56.4.94:9090"
	@echo "  Correlation: http://159.56.4.94:8080"
	@echo ""

# ============================================
# Pre-Setup Targets
# ============================================

##@ Setup

.PHONY: pre-setup
pre-setup: ## Run pre-setup checks (FIRST TIME ONLY)
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(GREEN)Running Pre-Setup Checks$(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@echo ""
	@if [ ! -f scripts/pre-setup.sh ]; then \
		echo "$(RED)❌ scripts/pre-setup.sh not found$(NC)"; \
		echo "Make sure you're in the repo root directory"; \
		exit 1; \
	fi
	@chmod +x scripts/pre-setup.sh 2>/dev/null || true
	@bash scripts/pre-setup.sh
	@echo ""
	@echo "$(GREEN)✓ Pre-setup complete! Next: make start-all$(NC)"

.PHONY: network-cleanup
network-cleanup: ## Fix Docker network conflicts
	@echo "$(YELLOW)→ Cleaning up Docker networks...$(NC)"
	@docker ps -q --filter "network=observability" 2>/dev/null | xargs -r docker stop 2>/dev/null || true
	@docker network rm observability 2>/dev/null || true
	@docker network prune -f >/dev/null 2>&1 || true
	@echo "$(GREEN)✓ Network cleanup complete$(NC)"

.PHONY: network-create
network-create: ## Create observability network
	@docker network create observability 2>/dev/null || true

# ============================================
# Observability Stack Targets
# ============================================

##@ Observability Stack

.PHONY: stack-up
stack-up: # network-create ## Start observability stack (Grafana/Loki/Tempo/Prometheus)
	@echo "$(YELLOW)→ Starting observability stack...$(NC)"
	@cd $(STACK_DIR) && $(DOCKER_COMPOSE) up -d
	@sleep 5
	@echo "$(GREEN)✓ Stack running. Grafana:  Grafana:     http://159.56.4.94:8443$(NC)"

.PHONY: stack-down
stack-down: ## Stop observability stack
	@echo "$(YELLOW)→ Stopping observability stack...$(NC)"
	@cd $(STACK_DIR) && $(DOCKER_COMPOSE) down
	@echo "$(GREEN)✓ Stack stopped$(NC)"

.PHONY: stack-logs
stack-logs: ## Tail observability stack logs
	@cd $(STACK_DIR) && $(DOCKER_COMPOSE) logs -f

.PHONY: stack-restart
stack-restart: stack-down stack-up ## Restart observability stack

# ============================================
# OTel Gateway Targets
# ============================================

##@ OTel Gateway

.PHONY: gateway-up
gateway-up: # network-create ## Start OTel Collector Gateway
	@echo "$(YELLOW)→ Starting OTel Collector Gateway...$(NC)"
	@cd $(GATEWAY_DIR) && $(DOCKER_COMPOSE) up -d
	@sleep 3
	@echo "$(GREEN)✓ Gateway running. OTLP: :55680 (gRPC), :55681 (HTTP)$(NC)"

.PHONY: gateway-down
gateway-down: ## Stop OTel Collector Gateway
	@echo "$(YELLOW)→ Stopping OTel Collector Gateway...$(NC)"
	@cd $(GATEWAY_DIR) && $(DOCKER_COMPOSE) down
	@echo "$(GREEN)✓ Gateway stopped$(NC)"

.PHONY: gateway-logs
gateway-logs: ## Tail OTel Gateway logs
	@cd $(GATEWAY_DIR) && $(DOCKER_COMPOSE) logs -f

.PHONY: gateway-restart
gateway-restart: gateway-down gateway-up ## Restart OTel Gateway

# ============================================
# Correlation Engine Targets
# ============================================

##@ Correlation Engine

.PHONY: corr-up
corr-up: #network-create ## Start Correlation Engine API
	@echo "$(YELLOW)→ Starting Correlation Engine API...$(NC)"
	@$(DOCKER_COMPOSE) up -d correlation-engine
	@sleep 3
	@echo "$(GREEN)✓ Correlation API running: http://159.56.4.94:8080$(NC)"

.PHONY: corr-down
corr-down: ## Stop Correlation Engine API
	@echo "$(YELLOW)→ Stopping Correlation Engine API...$(NC)"
	@$(DOCKER_COMPOSE) stop correlation-engine
	@$(DOCKER_COMPOSE) rm -f correlation-engine
	@echo "$(GREEN)✓ Correlation API stopped$(NC)"

.PHONY: corr-logs
corr-logs: ## Tail Correlation Engine logs
	@$(DOCKER_COMPOSE) logs -f correlation-engine

.PHONY: corr-restart
corr-restart: corr-down corr-up ## Restart Correlation Engine

# ============================================
# Sense Apps Targets
# ============================================

##@ Sense Applications

.PHONY: sense-up
sense-up: network-create ## Start Sense apps (Beorn/Palantir/Arda)
	@echo "$(YELLOW)→ Starting Sense apps...$(NC)"
	@cd $(SENSE_DIR) && make start-all
	@echo "$(GREEN)✓ Sense apps running: Beorn:5001, Palantir:5002, Arda:5003$(NC)"

.PHONY: sense-down
sense-down: ## Stop Sense apps
	@echo "$(YELLOW)→ Stopping Sense apps...$(NC)"
	@cd $(SENSE_DIR) && make stop-all
	@echo "$(GREEN)✓ Sense apps stopped$(NC)"

.PHONY: sense-logs
sense-logs: ## Tail Sense apps logs
	@cd $(SENSE_DIR) && tail -f beorn/logs/*.log palantir/logs/*.log arda/logs/*.log 2>/dev/null || \
		echo "$(YELLOW)No log files found yet$(NC)"

.PHONY: sense-restart
sense-restart: sense-down sense-up ## Restart Sense apps

# ============================================
# System Control Targets
# ============================================

##@ System Control

.PHONY: start-all
start-all: network-cleanup stack-up gateway-up corr-up ## Start all core services
	@echo ""
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(GREEN)✓ All core services started$(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@echo ""
	@echo "$(YELLOW)Service URLs:$(NC)"
	@echo "  Grafana:         Grafana:     http://159.56.4.94:8443"
	@echo "  Prometheus:     http://159.56.4.94:9090"
	@echo "  Loki:           http://159.56.4.94:3100"
	@echo "  Correlation:    http://159.56.4.94:8080"
	@echo ""
	@echo "$(YELLOW)Next steps:$(NC)"
	@echo "  make status        - Check service health"
	@echo "  make test-trace    - Send test telemetry"
	@echo "  make health        - Run full health check"
	@echo ""

.PHONY: stop-all
stop-all: ## Stop all services
	@echo "$(YELLOW)→ Stopping all services...$(NC)"
# 	@-$(MAKE) sense-down 2>/dev/null || true
	@-$(MAKE) corr-down 2>/dev/null || true
	@-$(MAKE) gateway-down 2>/dev/null || true
	@-$(MAKE) stack-down 2>/dev/null || true
	@docker network rm observability 2>/dev/null || true
	@echo "$(GREEN)✓ All services stopped$(NC)"

.PHONY: restart
restart: stop-all start-all ## Restart all services

.PHONY: up
up: start-all ## Alias for start-all

.PHONY: down
down: stop-all ## Alias for stop-all

# ============================================
# Local Development & Debugging
# ============================================

##@ Local Development

.PHONY: dev-setup
dev-setup: ## Setup local development environment
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(GREEN)Setting Up Local Development$(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@echo ""
	@echo "$(YELLOW)→ Creating .env file...$(NC)"
	@if [ ! -f .env ]; then \
		cp .env.example .env 2>/dev/null || echo "DEBUG=True" > .env; \
		echo "$(GREEN)✓ .env created$(NC)"; \
	else \
		echo "$(YELLOW)⚠ .env already exists$(NC)"; \
	fi
	@echo "$(YELLOW)→ Installing Python dependencies...$(NC)"
	@cd $(CORR_DIR) && pip install -r requirements.txt 2>/dev/null || echo "$(YELLOW)⚠ Install dependencies manually$(NC)"
	@echo "$(GREEN)✓ Dev setup complete$(NC)"

.PHONY: dev-run
dev-run: ## Run correlation engine locally (no Docker)
	@echo "$(YELLOW)→ Starting correlation engine locally...$(NC)"
	@cd $(CORR_DIR) && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

.PHONY: dev-test
dev-test: ## Run tests locally
	@echo "$(YELLOW)→ Running tests...$(NC)"
	@cd $(CORR_DIR) && pytest tests/ -v --cov=app

.PHONY: dev-lint
dev-lint: ## Run linting locally
	@echo "$(YELLOW)→ Running ruff linter...$(NC)"
	@cd $(CORR_DIR) && ruff check app/
	@echo "$(YELLOW)→ Running ruff formatter...$(NC)"
	@cd $(CORR_DIR) && ruff format --check app/

.PHONY: dev-format
dev-format: ## Format code with ruff
	@echo "$(YELLOW)→ Formatting code...$(NC)"
	@cd $(CORR_DIR) && ruff format app/
	@echo "$(GREEN)✓ Code formatted$(NC)"

.PHONY: dev-shell
dev-shell: ## Open Python shell with app context
	@cd $(CORR_DIR) && python -i -c "from app.main import app; from app import models, config"

##@ Debugging

.PHONY: debug-logs
debug-logs: ## Show detailed logs with timestamps
	@$(DOCKER_COMPOSE) logs -f --tail=100 --timestamps

.PHONY: debug-inspect
debug-inspect: ## Inspect correlation engine container
	@echo "$(BLUE)Container Details:$(NC)"
	@docker inspect correlation-engine 2>/dev/null | jq '.[0] | {State, NetworkSettings: .NetworkSettings.Networks}' || echo "$(YELLOW)Container not running$(NC)"

.PHONY: debug-env
debug-env: ## Show environment variables in container
	@echo "$(BLUE)Environment Variables:$(NC)"
	@docker exec correlation-engine env 2>/dev/null | sort || echo "$(YELLOW)Container not running$(NC)"

.PHONY: debug-network
debug-network: ## Debug Docker network connectivity
	@echo "$(BLUE)Network Connectivity:$(NC)"
	@docker network inspect observability 2>/dev/null | jq '.[0].Containers' || echo "$(YELLOW)Network not found$(NC)"

.PHONY: debug-ports
debug-ports: ## Show all exposed ports
	@echo "$(BLUE)Exposed Ports:$(NC)"
	@docker ps --format "table {{.Names}}\t{{.Ports}}" | grep -E "loki|tempo|grafana|prometheus|correlation|gateway"

.PHONY: debug-health
debug-health: ## Detailed health check with curl output
	@echo "$(BLUE)Detailed Health Checks:$(NC)"
	@echo ""
	@echo "$(YELLOW)Correlation Engine:$(NC)"
	@curl -v http://localhost:8080/health 2>&1 | grep -E "HTTP|Connected|health"
	@echo ""
	@echo "$(YELLOW)Grafana:$(NC)"
	@curl -v http://localhost:8443/api/health 2>&1 | grep -E "HTTP|Connected|health"
	@echo ""

.PHONY: debug-metrics-raw
debug-metrics-raw: ## Show raw metrics output
	@curl -s http://localhost:8080/metrics

.PHONY: debug-api
debug-api: ## Test correlation engine API endpoints
	@echo "$(BLUE)Testing API Endpoints:$(NC)"
	@echo ""
	@echo "$(YELLOW)Health:$(NC)"
	@curl -s http://localhost:8080/health | jq '.'
	@echo ""
	@echo "$(YELLOW)Metrics:$(NC)"
	@curl -s http://localhost:8080/metrics | head -20
	@echo ""
	@echo "$(YELLOW)Docs:$(NC)"
	@echo "  http://localhost:8080/docs"

##@ Testing

.PHONY: test-local
test-local: ## Run full local test suite
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(GREEN)Running Local Test Suite$(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@$(MAKE) dev-lint
	@$(MAKE) dev-test
	@echo "$(GREEN)✓ All tests passed$(NC)"

.PHONY: test-integration
test-integration: ## Run integration tests
	@echo "$(YELLOW)→ Running integration tests...$(NC)"
	@cd $(CORR_DIR) && pytest tests/ -v -m integration 2>/dev/null || \
		echo "$(YELLOW)No integration tests found$(NC)"

.PHONY: test-unit
test-unit: ## Run unit tests only
	@echo "$(YELLOW)→ Running unit tests...$(NC)"
	@cd $(CORR_DIR) && pytest tests/ -v -m "not integration"

.PHONY: test-coverage
test-coverage: ## Generate test coverage report
	@echo "$(YELLOW)→ Generating coverage report...$(NC)"
	@cd $(CORR_DIR) && pytest tests/ --cov=app --cov-report=html --cov-report=term
	@echo "$(GREEN)✓ Coverage report: $(CORR_DIR)/htmlcov/index.html$(NC)"

.PHONY: test-watch
test-watch: ## Run tests in watch mode
	@cd $(CORR_DIR) && pytest-watch tests/ -v

.PHONY: test-send-log
test-send-log: ## Send a single test log
	@echo "$(YELLOW)→ Sending test log...$(NC)"
	@curl -X POST http://localhost:8080/api/logs \
		-H "Content-Type: application/json" \
		-d '{ \
			"resource": {"service": "test-app", "host": "localhost", "env": "dev"}, \
			"records": [{ \
				"timestamp": "'$$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)'", \
				"severity": "INFO", \
				"message": "Test log from Makefile", \
				"trace_id": "'$$(openssl rand -hex 16)'" \
			}] \
		}' | jq '.'

.PHONY: test-send-trace
test-send-trace: ## Send a test trace
	@echo "$(YELLOW)→ Sending test trace...$(NC)"
	@python3 scripts/send-test-span.py 2>/dev/null || \
		echo "$(YELLOW)send-test-span.py not found$(NC)"

.PHONY: test-load
test-load: ## Run load test (100 requests)
	@echo "$(YELLOW)→ Running load test...$(NC)"
	@for i in {1..100}; do \
		curl -s -X POST http://localhost:8080/api/logs \
			-H "Content-Type: application/json" \
			-d '{"resource": {"service": "load-test", "host": "localhost"}, "records": [{"timestamp": "'$$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)'", "severity": "INFO", "message": "Load test $$i"}]}' \
			>/dev/null & \
	done
	@wait
	@echo "$(GREEN)✓ Load test complete$(NC)"

##@ Quick Fixes

.PHONY: fix-permissions
fix-permissions: ## Fix file permissions
	@echo "$(YELLOW)→ Fixing permissions...$(NC)"
	@chmod +x scripts/*.sh 2>/dev/null || true
	@chmod +x ops/*.sh 2>/dev/null || true
	@echo "$(GREEN)✓ Permissions fixed$(NC)"

.PHONY: fix-ports
fix-ports: ## Kill processes on conflicting ports
	@echo "$(YELLOW)→ Checking for port conflicts...$(NC)"
	@lsof -ti:8080 | xargs kill -9 2>/dev/null || echo "  Port 8080 clear"
	@lsof -ti:8443 | xargs kill -9 2>/dev/null || echo "  Port 8443 clear"
	@lsof -ti:9090 | xargs kill -9 2>/dev/null || echo "  Port 9090 clear"
	@echo "$(GREEN)✓ Ports cleared$(NC)"

.PHONY: fix-docker
fix-docker: ## Fix common Docker issues
	@echo "$(YELLOW)→ Fixing Docker issues...$(NC)"
	@docker system prune -f
	@$(MAKE) network-cleanup
	@$(MAKE) network-create
	@echo "$(GREEN)✓ Docker fixed$(NC)"

.PHONY: rebuild
rebuild: ## Rebuild all containers from scratch
	@echo "$(YELLOW)→ Rebuilding all containers...$(NC)"
	@$(DOCKER_COMPOSE) build --no-cache
	@echo "$(GREEN)✓ Rebuild complete$(NC)"

# ============================================
# Health & Monitoring Targets
# ============================================

##@ Health & Monitoring

.PHONY: health
health: ## Check health of all services
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(GREEN)Checking Health of All Services$(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@echo ""
	@echo "$(YELLOW)Grafana:$(NC)"
	@curl -sf http://localhost:8443/api/health >/dev/null 2>&1 && \
		echo "$(GREEN)  ✓ Healthy$(NC)" || echo "$(RED)  ✗ Unhealthy$(NC)"
	@echo "$(YELLOW)Loki:$(NC)"
	@curl -sf http://localhost:3100/ready >/dev/null 2>&1 && \
		echo "$(GREEN)  ✓ Ready$(NC)" || echo "$(RED)  ✗ Not Ready$(NC)"
	@echo "$(YELLOW)Tempo:$(NC)"
	@curl -sf http://localhost:3200/ready >/dev/null 2>&1 && \
		echo "$(GREEN)  ✓ Ready$(NC)" || echo "$(RED)  ✗ Not Ready$(NC)"
	@echo "$(YELLOW)Prometheus:$(NC)"
	@curl -sf http://localhost:9090/-/healthy >/dev/null 2>&1 && \
		echo "$(GREEN)  ✓ Healthy$(NC)" || echo "$(RED)  ✗ Unhealthy$(NC)"
	@echo "$(YELLOW)OTel Gateway:$(NC)"
	@curl -sf http://localhost:13133 >/dev/null 2>&1 && \
		echo "$(GREEN)  ✓ Healthy$(NC)" || echo "$(RED)  ✗ Unhealthy$(NC)"
	@echo "$(YELLOW)Correlation Engine:$(NC)"
	@curl -sf http://localhost:8080/health >/dev/null 2>&1 && \
		echo "$(GREEN)  ✓ Healthy$(NC)" || echo "$(RED)  ✗ Unhealthy$(NC)"
	@echo ""

.PHONY: health-check
health-check: health ## Alias for health

.PHONY: status
status: ## Show service status
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(GREEN)Service Status$(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@echo ""
	@echo "$(YELLOW)Observability Stack:$(NC)"
	@cd $(STACK_DIR) 2>/dev/null && $(DOCKER_COMPOSE) ps --format "table {{.Name}}\t{{.Status}}" 2>/dev/null || echo "  Not running"
	@echo ""
	@echo "$(YELLOW)OTel Gateway:$(NC)"
	@cd $(GATEWAY_DIR) 2>/dev/null && $(DOCKER_COMPOSE) ps --format "table {{.Name}}\t{{.Status}}" 2>/dev/null || echo "  Not running"
	@echo ""
	@echo "$(YELLOW)Correlation API:$(NC)"
	@cd $(CORR_DIR) 2>/dev/null && $(DOCKER_COMPOSE) ps --format "table {{.Name}}\t{{.Status}}" 2>/dev/null || echo "  Not running"
	@echo ""
	@echo "$(YELLOW)Docker Networks:$(NC)"
	@docker network ls | grep observability || echo "  No observability network found"
	@echo ""

.PHONY: ps
ps: status ## Alias for status

# ============================================
# Logging Targets
# ============================================

##@ Logging

.PHONY: logs
logs: ## Tail logs from all services
	@echo "$(YELLOW)Tailing all service logs (Ctrl+C to stop)...$(NC)"
	@$(DOCKER_COMPOSE) logs -f 2>/dev/null || \
		docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "loki|tempo|grafana|prometheus|correlation|gateway"

.PHONY: logs-grafana
logs-grafana: ## Tail Grafana logs
	@cd $(STACK_DIR) && $(DOCKER_COMPOSE) logs -f grafana

.PHONY: logs-loki
logs-loki: ## Tail Loki logs
	@cd $(STACK_DIR) && $(DOCKER_COMPOSE) logs -f loki

.PHONY: logs-tempo
logs-tempo: ## Tail Tempo logs
	@cd $(STACK_DIR) && $(DOCKER_COMPOSE) logs -f tempo

.PHONY: logs-prometheus
logs-prometheus: ## Tail Prometheus logs
	@cd $(STACK_DIR) && $(DOCKER_COMPOSE) logs -f prometheus

.PHONY: logs-engine
logs-engine: corr-logs ## Alias for correlation engine logs

.PHONY: logs-gateway
logs-gateway: gateway-logs ## Alias for gateway logs

.PHONY: logs-otel
logs-otel: ## Tail OTel Collector logs
	@docker logs -f otel-gateway 2>/dev/null || \
		echo "$(YELLOW)OTel Gateway container not running$(NC)"

.PHONY: logs-sense
logs-sense: sense-logs ## Alias for sense app logs

# ============================================
# Testing Targets
# ============================================

##@ Testing

.PHONY: test-logs
test-logs: ## Send test logs to correlation engine
	@echo "$(GREEN)→ Sending test logs...$(NC)"
	@curl -X POST http://localhost:8080/api/logs \
		-H "Content-Type: application/json" \
		-d '{"resource": {"service": "test", "host": "localhost", "env": "dev"}, "records": [{"timestamp": "'$$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)'", "severity": "INFO", "message": "Test log from Makefile", "labels": {"source": "makefile"}, "trace_id": "12345678901234567890123456789012"}]}' \
		>/dev/null 2>&1 && echo "$(GREEN)✓ Test logs sent$(NC)" || echo "$(RED)✗ Failed to send logs$(NC)"

.PHONY: test-trace
test-trace: ## Generate test traces from sense apps
	@echo "$(GREEN)→ Generating test traces...$(NC)"
	@curl -s http://localhost:5001/api/test 2>/dev/null | jq '.' 2>/dev/null || echo "$(YELLOW)Beorn not available$(NC)"
	@curl -s http://localhost:5002/api/test 2>/dev/null | jq '.' 2>/dev/null || echo "$(YELLOW)Palantir not available$(NC)"
	@curl -s http://localhost:5003/api/test 2>/dev/null | jq '.' 2>/dev/null || echo "$(YELLOW)Arda not available$(NC)"
	@echo "$(GREEN)✓ Test trace generation complete$(NC)"

.PHONY: test-span
test-span: test-trace ## Alias for test-trace

.PHONY: test-traffic
test-traffic: ## Generate test traffic across all services
	@if [ -f ops/test-traffic.sh ]; then \
		./ops/test-traffic.sh; \
	else \
		echo "$(YELLOW)test-traffic.sh not found, using basic test$(NC)"; \
		$(MAKE) test-logs; \
		$(MAKE) test-trace; \
	fi

.PHONY: stress-test
stress-test: ## Run stress test
	@echo "$(YELLOW)→ Running stress test...$(NC)"
	@if [ -f ops/stress-test.sh ]; then \
		./ops/stress-test.sh; \
	else \
		echo "$(RED)stress-test.sh not found$(NC)"; \
	fi

# ============================================
# Metrics & Observability Targets
# ============================================

##@ Metrics & Observability

.PHONY: metrics
metrics: ## Show correlation engine metrics
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(GREEN)Correlation Engine Metrics$(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@curl -s http://localhost:8080/metrics 2>/dev/null | \
		grep -E "^(correlation_|log_records_|traces_received_|export_)" | head -20 || \
		echo "$(YELLOW)Metrics endpoint not available$(NC)"
	@echo ""

.PHONY: correlations
correlations: ## Query recent correlations
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(GREEN)Recent Correlation Events$(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@curl -s "http://localhost:8080/api/correlations?limit=10" 2>/dev/null | jq '.' || \
		echo "$(YELLOW)Correlations API not available$(NC)"

.PHONY: prometheus-query
prometheus-query: ## Query Prometheus metrics
	@echo "$(YELLOW)Query: correlation_events_total$(NC)"
	@curl -s 'http://localhost:9090/api/v1/query?query=correlation_events_total' 2>/dev/null | \
		jq '.data.result' 2>/dev/null || echo "$(YELLOW)Prometheus not available$(NC)"

.PHONY: tail-loki
tail-loki: ## Query recent logs from Loki
	@echo "$(BLUE)Recent logs from Loki:$(NC)"
	@curl -s -G 'http://localhost:3100/loki/api/v1/query' \
		--data-urlencode 'query={service=~".+"}' \
		--data-urlencode 'limit=20' 2>/dev/null | \
		jq '.data.result[].values[]' 2>/dev/null || \
		echo "$(YELLOW)Loki not available$(NC)"

.PHONY: tail-tempo
tail-tempo: ## Query recent traces from Tempo
	@echo "$(BLUE)Recent traces from Tempo:$(NC)"
	@curl -s 'http://localhost:3200/api/search?tags=service.name=beorn&limit=10' 2>/dev/null | \
		jq '.' 2>/dev/null || echo "$(YELLOW)Tempo not available$(NC)"

# ============================================
# Browser/UI Targets
# ============================================

##@ User Interface

.PHONY: open-grafana
open-grafana: ## Open Grafana in browser
	@echo "$(GREEN)→ Opening Grafana...$(NC)"
	@if command -v open >/dev/null 2>&1; then \
		open  Grafana:     http://159.56.4.94:8443; \
	elif command -v xdg-open >/dev/null 2>&1; then \
		xdg-open  Grafana:     http://159.56.4.94:8443; \
	else \
		echo "Open:  Grafana:     http://159.56.4.94:8443"; \
	fi

.PHONY: open-dashboard
open-dashboard: ## Open Correlation Dashboard in Grafana
	@echo "$(GREEN)→ Opening Correlation Dashboard...$(NC)"
	@if command -v open >/dev/null 2>&1; then \
		open  Grafana:     http://159.56.4.94:8443/d/correlation-overview; \
	elif command -v xdg-open >/dev/null 2>&1; then \
		xdg-open  Grafana:     http://159.56.4.94:8443/d/correlation-overview; \
	else \
		echo "Open:  Grafana:     http://159.56.4.94:8443/d/correlation-overview"; \
	fi

# ============================================
# Documentation Targets
# ============================================

##@ Documentation

.PHONY: docs
docs: ## Show documentation links
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(GREEN)Documentation$(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@echo ""
	@echo "$(YELLOW)Service URLs:$(NC)"
	@echo "  Grafana:      Grafana:     http://159.56.4.94:8443"
	@echo "  Prometheus:  http://159.56.4.94:9090"
	@echo "  Correlation: http://159.56.4.94:8080"
	@echo ""
	@echo "$(YELLOW)Documentation:$(NC)"
	@echo "  README:    cat README.md"
	@echo "  Runbook:   cat ops/runbook.md"
	@echo "  API Docs:  http://159.56.4.94:8080/docs"
	@echo ""

# ============================================
# Cleanup Targets
# ============================================

##@ Cleanup

.PHONY: clean
clean: down ## Stop services and remove volumes
	@echo "$(RED)→ Removing volumes...$(NC)"
	@cd $(STACK_DIR) 2>/dev/null && $(DOCKER_COMPOSE) down -v || true
	@cd $(GATEWAY_DIR) 2>/dev/null && $(DOCKER_COMPOSE) down -v || true
	@cd $(CORR_DIR) 2>/dev/null && $(DOCKER_COMPOSE) down -v || true
	@docker network rm observability 2>/dev/null || true
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

.PHONY: purge
purge: clean ## Remove everything including images
	@echo "$(RED)→ Removing images...$(NC)"
	@docker images | grep -E "loki|tempo|grafana|prometheus|correlation|gateway|otel" | \
		awk '{print $$3}' | xargs -r docker rmi -f 2>/dev/null || true
	@echo "$(GREEN)✓ Purge complete$(NC)"

.PHONY: prune
prune: ## Remove unused Docker resources
	@echo "$(YELLOW)→ Pruning unused Docker resources...$(NC)"
	@docker system prune -f
	@echo "$(GREEN)✓ Prune complete$(NC)"

.PHONY: cleanup-all
cleanup-all: ## Full teardown (DEV ONLY - DELETES ALL DATA)
	@echo "$(RED)⚠️  WARNING: This will DELETE all data (logs, traces, metrics)$(NC)"
	@read -p "Continue? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	@if [ -f scripts/cleanup-dev.sh ]; then \
		bash scripts/cleanup-dev.sh; \
	else \
		$(MAKE) purge; \
	fi
	@docker network rm observability 2>/dev/null || true
	@echo "$(GREEN)✓ Full cleanup complete$(NC)"

# ============================================
# Development Targets
# ============================================

##@ Development

.PHONY: cd-om
cd-om: ## Change to seefa-om directory
	@cd $(OM_DIR) && exec $$SHELL

.PHONY: cd-sense
cd-sense: ## Change to sense-test directory
	@cd $(SENSE_TEST_DIR) && exec $$SHELL

.PHONY: cd-nginx
cd-nginx: ## Change to nginx conf directory
	@cd $(NGINX_CONF_DIR) && exec $$SHELL

.PHONY: edit
edit: ## Remove and edit file (usage: make edit FILE=path/to/file)
	@if [ -z "$(FILE)" ]; then \
		echo "$(RED)Error: FILE parameter required$(NC)"; \
		echo "Usage: make edit FILE=path/to/file"; \
		exit 1; \
	fi
	@sudo rm -rf $(FILE)
	@sudo vi $(FILE)

.PHONY: pull
pull: ## Pull latest from develop branch
	@echo "$(YELLOW)→ Pulling from origin/develop...$(NC)"
	@git pull origin develop
	@echo "$(GREEN)✓ Pull complete$(NC)"

.PHONY: shell-engine
shell-engine: ## Open shell in correlation engine container
	@docker exec -it correlation-engine /bin/bash 2>/dev/null || \
		echo "$(YELLOW)Correlation engine not running$(NC)"

.PHONY: shell-gateway
shell-gateway: ## Open shell in OTel gateway container
	@docker exec -it otel-gateway /bin/sh 2>/dev/null || \
		echo "$(YELLOW)OTel gateway not running$(NC)"

.PHONY: shell-otel
shell-otel: shell-gateway ## Alias for OTel gateway shell

.PHONY: shell-grafana
shell-grafana: ## Open shell in Grafana container
	@docker exec -it grafana /bin/sh 2>/dev/null || \
		echo "$(YELLOW)Grafana not running$(NC)"

# ============================================
# Advanced Targets
# ============================================

##@ Advanced

.PHONY: backup-dashboards
backup-dashboards: ## Backup Grafana dashboards
	@mkdir -p backups/dashboards
	@echo "$(YELLOW)→ Backing up dashboards...$(NC)"
	@curl -s http://admin:admin@localhost:3000/api/search 2>/dev/null | \
		jq -r '.[].uid' 2>/dev/null | \
		while read uid; do \
			echo "  Backing up dashboard: $$uid"; \
			curl -s http://admin:admin@localhost:3000/api/dashboards/uid/$$uid 2>/dev/null | \
				jq '.dashboard' > backups/dashboards/$$uid.json; \
		done || echo "$(YELLOW)Could not backup dashboards$(NC)"
	@echo "$(GREEN)✓ Dashboards backed up to backups/dashboards/$(NC)"

.PHONY: restore-dashboards
restore-dashboards: ## Restore Grafana dashboards from backup
	@if [ ! -d backups/dashboards ]; then \
		echo "$(RED)No backup directory found$(NC)"; \
		exit 1; \
	fi
	@for file in backups/dashboards/*.json; do \
		if [ -f "$$file" ]; then \
			echo "Restoring dashboard: $$file"; \
			jq -n --argfile dashboard "$$file" '{dashboard: $$dashboard, overwrite: true}' | \
				curl -X POST http://admin:admin@localhost:3000/api/dashboards/db \
					-H "Content-Type: application/json" \
					-d @- >/dev/null 2>&1; \
		fi \
	done
	@echo "$(GREEN)✓ Dashboards restored$(NC)"

.PHONY: check-disk
check-disk: ## Check disk usage
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(GREEN)Disk Usage$(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@echo ""
	@echo "$(YELLOW)Overall:$(NC)"
	@df -h / | tail -1
	@echo ""
	@echo "$(YELLOW)Docker Volumes:$(NC)"
	@docker system df -v 2>/dev/null | grep -A 20 "VOLUME NAME" || \
		docker system df

.PHONY: check-cardinality
check-cardinality: ## Check Loki label cardinality
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(GREEN)Loki Label Cardinality$(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@curl -s http://localhost:3100/loki/api/v1/labels 2>/dev/null | jq '.' || \
		echo "$(YELLOW)Loki not available$(NC)"
	@echo ""
	@echo "$(YELLOW)Values per label:$(NC)"
	@for label in $$(curl -s http://localhost:3100/loki/api/v1/labels 2>/dev/null | jq -r '.data[]' 2>/dev/null); do \
		count=$$(curl -s http://localhost:3100/loki/api/v1/label/$$label/values 2>/dev/null | jq '.data | length' 2>/dev/null); \
		echo "  $$label: $$count values"; \
	done 2>/dev/null || echo "$(YELLOW)Cannot retrieve label cardinality$(NC)"

# ============================================
# CI/CD Targets
# ============================================

##@ CI/CD

.PHONY: ci-build
ci-build: ## Build for CI (no cache)
	@echo "$(YELLOW)→ Building images for CI...$(NC)"
	@cd $(STACK_DIR) && $(DOCKER_COMPOSE) build --no-cache --parallel
	@cd $(GATEWAY_DIR) && $(DOCKER_COMPOSE) build --no-cache
	@cd $(CORR_DIR) && $(DOCKER_COMPOSE) build --no-cache
	@echo "$(GREEN)✓ CI build complete$(NC)"

.PHONY: ci-test
ci-test: up ## Run CI tests
	@echo "$(YELLOW)→ Running CI tests...$(NC)"
	@sleep 30  # Wait for services to be ready
	@$(MAKE) health
	@$(MAKE) test-logs
	@$(MAKE) test-trace
	@echo "$(GREEN)✓ CI tests passed$(NC)"

.PHONY: ci-cleanup
ci-cleanup: ## Cleanup CI resources
	@echo "$(YELLOW)→ Cleaning up CI resources...$(NC)"
	@$(MAKE) down
	@docker system prune -af --volumes
	@echo "$(GREEN)✓ CI cleanup complete$(NC)"

# ============================================
# Validation Targets
# ============================================

##@ Validation

.PHONY: validate
validate: validate-compose validate-env validate-network ## Run all validations

.PHONY: validate-compose
validate-compose: ## Validate Docker Compose files
	@echo "$(YELLOW)→ Validating Docker Compose files...$(NC)"
	@cd $(STACK_DIR) && $(DOCKER_COMPOSE) config >/dev/null 2>&1 && \
		echo "$(GREEN)  ✓ $(STACK_DIR)/docker-compose.yml$(NC)" || \
		echo "$(RED)  ✗ $(STACK_DIR)/docker-compose.yml$(NC)"
	@cd $(GATEWAY_DIR) && $(DOCKER_COMPOSE) config >/dev/null 2>&1 && \
		echo "$(GREEN)  ✓ $(GATEWAY_DIR)/docker-compose.yml$(NC)" || \
		echo "$(RED)  ✗ $(GATEWAY_DIR)/docker-compose.yml$(NC)"
	@cd $(CORR_DIR) && $(DOCKER_COMPOSE) config >/dev/null 2>&1 && \
		echo "$(GREEN)  ✓ $(CORR_DIR)/docker-compose.yml$(NC)" || \
		echo "$(RED)  ✗ $(CORR_DIR)/docker-compose.yml$(NC)"

.PHONY: validate-env
validate-env: ## Validate environment variables
	@echo "$(YELLOW)→ Validating environment...$(NC)"
	@if [ -f .env ]; then \
		echo "$(GREEN)  ✓ .env file exists$(NC)"; \
		grep -q "ARTIFACTORY_USER" .env && \
			echo "$(GREEN)  ✓ ARTIFACTORY_USER configured$(NC)" || \
			echo "$(YELLOW)  ⚠ ARTIFACTORY_USER not set$(NC)"; \
		grep -q "ARTIFACTORY_TOKEN" .env && \
			echo "$(GREEN)  ✓ ARTIFACTORY_TOKEN configured$(NC)" || \
			echo "$(YELLOW)  ⚠ ARTIFACTORY_TOKEN not set$(NC)"; \
	else \
		echo "$(YELLOW)  ⚠ .env file not found$(NC)"; \
	fi

.PHONY: validate-network
validate-network: ## Validate Docker network
	@echo "$(YELLOW)→ Validating Docker network...$(NC)"
	@docker network ls | grep -q observability && \
		echo "$(GREEN)  ✓ observability network exists$(NC)" || \
		echo "$(YELLOW)  ⚠ observability network not found (will be created)$(NC)"

# ============================================
# Deprecated/Legacy Targets (for compatibility)
# ============================================

.PHONY: poller-install
poller-install: ## [DEPRECATED] Poller has been removed
	@echo "$(YELLOW)⚠️  The poller component has been deprecated and removed.$(NC)"
	@echo "   Grafana Alloy now handles log streaming directly."

.PHONY: poller-start
poller-start: poller-install ## [DEPRECATED] Poller has been removed

.PHONY: poller-stop
poller-stop: ## [DEPRECATED] Poller has been removed
	@echo "$(YELLOW)⚠️  The poller component has been deprecated and removed.$(NC)"

.PHONY: poller-status
poller-status: ## [DEPRECATED] Poller has been removed
	@echo "$(YELLOW)⚠️  The poller component has been deprecated and removed.$(NC)"

.PHONY: poller-logs
poller-logs: ## [DEPRECATED] Poller has been removed
	@echo "$(YELLOW)⚠️  The poller component has been deprecated and removed.$(NC)"

# ============================================
# End of Makefile
# ============================================