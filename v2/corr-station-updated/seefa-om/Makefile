# ============================================
# Correlation Station - Enhanced Makefile
# Complete Manual Setup & Operations
# ============================================
# Author: derrick.golden@chater.com
# Purpose: Complete orchestration for observability stack
# Version: 2.0.0 - Enhanced with full manual setup
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
PURPLE := \033[0;35m
CYAN := \033[0;36m
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
K6_DIR := k6
FRONTEND_DIR := frontend

# Common paths
OM_DIR := /opt/correlation-station/seefa-om
SENSE_TEST_DIR := /opt/correlation-station/sense-test
NGINX_CONF_DIR := /etc/nginx/conf.d

# Timestamp for backups
TIMESTAMP := $(shell date +%Y%m%d_%H%M%S)

# Backup directory
BACKUP_DIR := backups/$(TIMESTAMP)

# ============================================
# Help Target
# ============================================
.PHONY: help
help: ## Show this help message
	@printf "$(BLUE)========================================$(NC)\n"
	@printf "$(GREEN)Correlation Station - Enhanced Manual Setup$(NC)\n"
	@printf "$(BLUE)========================================$(NC)\n"
	@awk 'BEGIN {FS = ":.*##"; printf "\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  $(YELLOW)%-25s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(BLUE)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(BLUE)Quick Start (Automated):$(NC)"
	@echo "  1. make setup-validate     # Validate prerequisites"
	@echo "  2. make setup-all          # Complete automated setup"
	@echo "  3. make health-full        # Verify all services"
	@echo ""
	@echo "$(BLUE)Manual Setup (Step-by-step):$(NC)"
	@echo "  1. make setup-prerequisites # Install dependencies"
	@echo "  2. make setup-network       # Create Docker network"
	@echo "  3. make setup-observability # Setup Grafana, Loki, etc"
	@echo "  4. make setup-gateway       # Setup OTel Gateway"
	@echo "  5. make setup-correlation   # Setup Correlation Engine"
	@echo "  6. make setup-redis         # Setup Redis"
	@echo "  7. make setup-sense-apps    # Setup Sense apps"
	@echo "  8. make setup-frontend      # Setup UI"
	@echo ""
	@echo "$(BLUE)Service URLs:$(NC)"
	@echo "  Frontend:    http://localhost:3000"
	@echo "  Grafana:     http://159.56.4.94:8443"
	@echo "  Prometheus:  http://159.56.4.94:9090"
	@echo "  Correlation: http://159.56.4.94:8080"
	@echo "  Pyroscope:   http://localhost:4040"
	@echo "  Redis:       localhost:6379"
	@echo ""

# ============================================
# Setup & Installation Targets
# ============================================

##@ Setup & Installation

.PHONY: setup-validate
setup-validate: ## Validate prerequisites and environment
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(GREEN)Validating Prerequisites$(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@echo ""
	@echo "$(YELLOW)→ Checking Docker...$(NC)"
	@docker --version >/dev/null 2>&1 && \
		echo "$(GREEN)  ✓ Docker installed: $$(docker --version)$(NC)" || \
		(echo "$(RED)  ✗ Docker not found - Install: https://docs.docker.com/get-docker/$(NC)" && exit 1)
	@echo "$(YELLOW)→ Checking Docker Compose...$(NC)"
	@$(DOCKER_COMPOSE) version >/dev/null 2>&1 && \
		echo "$(GREEN)  ✓ Docker Compose installed$(NC)" || \
		(echo "$(RED)  ✗ Docker Compose not found$(NC)" && exit 1)
	@echo "$(YELLOW)→ Checking disk space...$(NC)"
	@df -h . | awk 'NR==2 {if (substr($$4,1,length($$4)-1)+0 < 20) {print "$(RED)  ✗ Low disk space: "$$4" available (need 20GB+)$(NC)"; exit 1} else print "$(GREEN)  ✓ Disk space OK: "$$4" available$(NC)"}'
	@echo "$(YELLOW)→ Checking memory...$(NC)"
	@free -h | awk '/^Mem:/ {print "$(GREEN)  ✓ Memory available: "$$2" total$(NC)"}'
	@echo "$(YELLOW)→ Checking required ports...$(NC)"
	@for port in 3000 3100 4040 5001 5002 5003 6379 8080 8443 9000 9090 55681; do \
		if lsof -Pi :$$port -sTCP:LISTEN -t >/dev/null 2>&1 ; then \
			echo "$(RED)  ✗ Port $$port is in use$(NC)"; \
		else \
			echo "$(GREEN)  ✓ Port $$port available$(NC)"; \
		fi \
	done
	@echo ""
	@echo "$(GREEN)✓ Validation complete!$(NC)"

.PHONY: setup-prerequisites
setup-prerequisites: ## Install required tools and dependencies
	@echo "$(YELLOW)→ Installing prerequisites...$(NC)"
	@if [ ! -f scripts/pre-setup.sh ]; then \
		echo "$(RED)❌ scripts/pre-setup.sh not found$(NC)"; \
		exit 1; \
	fi
	@chmod +x scripts/pre-setup.sh 2>/dev/null || true
	@bash scripts/pre-setup.sh
	@echo "$(GREEN)✓ Prerequisites installed$(NC)"

.PHONY: setup-network
setup-network: ## Create Docker network
	@echo "$(YELLOW)→ Creating observability network...$(NC)"
	@docker network create observability \
		--driver bridge \
		--subnet 172.20.0.0/23 \
		2>/dev/null || echo "$(YELLOW)  Network already exists$(NC)"
	@docker network inspect observability >/dev/null 2>&1 && \
		echo "$(GREEN)✓ Network ready$(NC)" || \
		(echo "$(RED)✗ Network creation failed$(NC)" && exit 1)

.PHONY: setup-observability
setup-observability: setup-network ## Setup observability stack (Grafana, Loki, Tempo, Prometheus, Pyroscope)
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(GREEN)Setting Up Observability Stack$(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@echo ""
	@echo "$(YELLOW)→ Starting Grafana...$(NC)"
	@$(DOCKER_COMPOSE) up -d grafana
	@sleep 5
	@echo "$(GREEN)  ✓ Grafana started on :8443$(NC)"
	@echo ""
	@echo "$(YELLOW)→ Starting Loki...$(NC)"
	@$(DOCKER_COMPOSE) up -d loki
	@sleep 3
	@echo "$(GREEN)  ✓ Loki started on :3100$(NC)"
	@echo ""
	@echo "$(YELLOW)→ Starting Tempo...$(NC)"
	@$(DOCKER_COMPOSE) up -d tempo
	@sleep 3
	@echo "$(GREEN)  ✓ Tempo started on :9000$(NC)"
	@echo ""
	@echo "$(YELLOW)→ Starting Prometheus...$(NC)"
	@$(DOCKER_COMPOSE) up -d prometheus
	@sleep 3
	@echo "$(GREEN)  ✓ Prometheus started on :9090$(NC)"
	@echo ""
	@echo "$(YELLOW)→ Starting Pyroscope...$(NC)"
	@$(DOCKER_COMPOSE) up -d pyroscope
	@sleep 3
	@echo "$(GREEN)  ✓ Pyroscope started on :4040$(NC)"
	@echo ""
	@echo "$(YELLOW)→ Waiting for services to be healthy (30s)...$(NC)"
	@sleep 30
	@$(MAKE) health-observability
	@echo ""
	@echo "$(GREEN)✓ Observability stack setup complete!$(NC)"
	@echo ""
	@echo "$(CYAN)Access:$(NC)"
	@echo "  Grafana:    http://159.56.4.94:8443 (admin/admin)"
	@echo "  Prometheus: http://159.56.4.94:9090"
	@echo "  Pyroscope:  http://localhost:4040"

.PHONY: setup-gateway
setup-gateway: setup-observability ## Setup OTel Gateway
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(GREEN)Setting Up OTel Gateway$(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@echo ""
	@echo "$(YELLOW)→ Starting OTel Collector Gateway...$(NC)"
	@$(DOCKER_COMPOSE) up -d otel-gateway
	@sleep 5
	@echo "$(GREEN)  ✓ Gateway started$(NC)"
	@echo ""
	@echo "$(YELLOW)→ Checking health...$(NC)"
	@sleep 3
	@curl -sf http://localhost:13133 >/dev/null 2>&1 && \
		echo "$(GREEN)  ✓ Gateway healthy$(NC)" || \
		echo "$(RED)  ✗ Gateway unhealthy$(NC)"
	@echo ""
	@echo "$(GREEN)✓ OTel Gateway setup complete!$(NC)"
	@echo ""
	@echo "$(CYAN)Endpoints:$(NC)"
	@echo "  OTLP HTTP: http://localhost:55681"
	@echo "  OTLP gRPC: localhost:4317 (internal)"
	@echo "  Health:    http://localhost:13133"
	@echo "  Metrics:   http://localhost:8888/metrics"

.PHONY: setup-correlation
setup-correlation: setup-gateway ## Setup Correlation Engine
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(GREEN)Setting Up Correlation Engine$(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@echo ""
	@echo "$(YELLOW)→ Building correlation engine...$(NC)"
	@$(DOCKER_COMPOSE) build correlation-engine
	@echo "$(YELLOW)→ Starting correlation engine...$(NC)"
	@$(DOCKER_COMPOSE) up -d correlation-engine
	@sleep 5
	@echo ""
	@echo "$(YELLOW)→ Checking health...$(NC)"
	@sleep 3
	@curl -sf http://localhost:8080/health >/dev/null 2>&1 && \
		echo "$(GREEN)  ✓ Correlation engine healthy$(NC)" || \
		echo "$(RED)  ✗ Correlation engine unhealthy$(NC)"
	@echo ""
	@echo "$(GREEN)✓ Correlation Engine setup complete!$(NC)"
	@echo ""
	@echo "$(CYAN)Access:$(NC)"
	@echo "  API:     http://159.56.4.94:8080"
	@echo "  Docs:    http://159.56.4.94:8080/docs"
	@echo "  Health:  http://159.56.4.94:8080/health"
	@echo "  Metrics: http://159.56.4.94:8080/metrics"

.PHONY: setup-redis
setup-redis: setup-network ## Setup Redis for horizontal scaling
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(GREEN)Setting Up Redis$(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@echo ""
	@echo "$(YELLOW)→ Starting Redis...$(NC)"
	@$(DOCKER_COMPOSE) up -d redis
	@sleep 3
	@echo ""
	@echo "$(YELLOW)→ Checking health...$(NC)"
	@docker exec redis redis-cli ping >/dev/null 2>&1 && \
		echo "$(GREEN)  ✓ Redis healthy (PONG)$(NC)" || \
		echo "$(RED)  ✗ Redis unhealthy$(NC)"
	@echo ""
	@echo "$(YELLOW)→ Redis info...$(NC)"
	@docker exec redis redis-cli info server | grep -E "redis_version|os|arch" || true
	@echo ""
	@echo "$(GREEN)✓ Redis setup complete!$(NC)"
	@echo ""
	@echo "$(CYAN)Connection:$(NC)"
	@echo "  Host: localhost"
	@echo "  Port: 6379"
	@echo "  URL:  redis://localhost:6379"
	@echo ""
	@echo "$(YELLOW)Next: Enable Redis in correlation engine$(NC)"
	@echo "  1. Edit correlation-engine/.env"
	@echo "  2. Set: USE_REDIS_STATE=true"
	@echo "  3. Set: REDIS_URL=redis://redis:6379"
	@echo "  4. Run: make corr-restart"

.PHONY: setup-sense-apps
setup-sense-apps: setup-gateway ## Setup Sense applications (Beorn, Palantir, Arda)
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(GREEN)Setting Up Sense Applications$(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@echo ""
	@echo "$(YELLOW)→ Building Beorn...$(NC)"
	@$(DOCKER_COMPOSE) build beorn
	@echo "$(YELLOW)→ Starting Beorn...$(NC)"
	@$(DOCKER_COMPOSE) up -d beorn
	@sleep 5
	@curl -sf http://localhost:5001/health >/dev/null 2>&1 && \
		echo "$(GREEN)  ✓ Beorn healthy on :5001$(NC)" || \
		echo "$(YELLOW)  ⚠ Beorn starting...$(NC)"
	@echo ""
	@echo "$(YELLOW)→ Building Palantir...$(NC)"
	@$(DOCKER_COMPOSE) build palantir
	@echo "$(YELLOW)→ Starting Palantir...$(NC)"
	@$(DOCKER_COMPOSE) up -d palantir
	@sleep 5
	@curl -sf http://localhost:5002/health >/dev/null 2>&1 && \
		echo "$(GREEN)  ✓ Palantir healthy on :5002$(NC)" || \
		echo "$(YELLOW)  ⚠ Palantir starting...$(NC)"
	@echo ""
	@echo "$(YELLOW)→ Building Arda...$(NC)"
	@$(DOCKER_COMPOSE) build arda
	@echo "$(YELLOW)→ Starting Arda...$(NC)"
	@$(DOCKER_COMPOSE) up -d arda
	@sleep 5
	@curl -sf http://localhost:5003/health >/dev/null 2>&1 && \
		echo "$(GREEN)  ✓ Arda healthy on :5003$(NC)" || \
		echo "$(YELLOW)  ⚠ Arda starting...$(NC)"
	@echo ""
	@echo "$(GREEN)✓ Sense apps setup complete!$(NC)"
	@echo ""
	@echo "$(CYAN)Access:$(NC)"
	@echo "  Beorn:    http://localhost:5001"
	@echo "  Palantir: http://localhost:5002"
	@echo "  Arda:     http://localhost:5003"

.PHONY: restart-sense-apps
restart-sense-apps: ## Restart Sense apps (stops, removes old containers, and recreates)
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(GREEN)Restarting Sense Applications$(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@echo ""
	@echo "$(YELLOW)→ Stopping and removing old containers...$(NC)"
	@$(DOCKER_COMPOSE) stop beorn palantir arda 2>/dev/null || true
	@$(DOCKER_COMPOSE) rm -f beorn palantir arda 2>/dev/null || true
	@echo "$(GREEN)✓ Old containers removed$(NC)"
	@echo ""
	@$(MAKE) setup-sense-apps

.PHONY: setup-frontend
setup-frontend: setup-correlation ## Setup Frontend UI
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(GREEN)Setting Up Frontend UI$(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@echo ""
	@echo "$(YELLOW)→ Building frontend...$(NC)"
	@$(DOCKER_COMPOSE) build correlation-station-ui
	@echo "$(YELLOW)→ Starting frontend...$(NC)"
	@$(DOCKER_COMPOSE) up -d correlation-station-ui
	@sleep 5
	@echo ""
	@echo "$(YELLOW)→ Checking health...$(NC)"
	@curl -sf http://localhost:3000 >/dev/null 2>&1 && \
		echo "$(GREEN)  ✓ Frontend healthy$(NC)" || \
		echo "$(YELLOW)  ⚠ Frontend starting...$(NC)"
	@echo ""
	@echo "$(GREEN)✓ Frontend UI setup complete!$(NC)"
	@echo ""
	@echo "$(CYAN)Access:$(NC)"
	@echo "  URL: http://localhost:3000"

.PHONY: setup-all
setup-all: setup-validate ## Complete automated setup (all components)
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(GREEN)Complete Automated Setup$(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@echo ""
	@$(MAKE) setup-network
	@echo ""
	@$(MAKE) setup-observability
	@echo ""
	@$(MAKE) setup-gateway
	@echo ""
	@$(MAKE) setup-redis
	@echo ""
	@$(MAKE) setup-correlation
	@echo ""
	@$(MAKE) setup-sense-apps
	@echo ""
	@$(MAKE) setup-frontend
	@echo ""
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(GREEN)✓ Complete Setup Finished!$(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@echo ""
	@echo "$(YELLOW)Run health check:$(NC)"
	@echo "  make health-full"
	@echo ""
	@echo "$(YELLOW)Generate test data:$(NC)"
	@echo "  make test-traffic"
	@echo ""
	@echo "$(YELLOW)Access UIs:$(NC)"
	@echo "  Frontend:   http://localhost:3000"
	@echo "  Grafana:    http://159.56.4.94:8443"
	@echo "  Prometheus: http://159.56.4.94:9090"

# ============================================
# Teardown Targets
# ============================================

##@ Teardown & Cleanup

.PHONY: teardown-sense-apps
teardown-sense-apps: ## Stop and remove Sense apps
	@echo "$(YELLOW)→ Stopping Sense apps...$(NC)"
	@$(DOCKER_COMPOSE) stop beorn palantir arda 2>/dev/null || true
	@$(DOCKER_COMPOSE) rm -f beorn palantir arda 2>/dev/null || true
	@echo "$(GREEN)✓ Sense apps removed$(NC)"

.PHONY: teardown-frontend
teardown-frontend: ## Stop and remove Frontend UI
	@echo "$(YELLOW)→ Stopping Frontend UI...$(NC)"
	@$(DOCKER_COMPOSE) stop correlation-station-ui 2>/dev/null || true
	@$(DOCKER_COMPOSE) rm -f correlation-station-ui 2>/dev/null || true
	@echo "$(GREEN)✓ Frontend removed$(NC)"

.PHONY: teardown-redis
teardown-redis: ## Stop and remove Redis
	@echo "$(YELLOW)→ Stopping Redis...$(NC)"
	@$(DOCKER_COMPOSE) stop redis 2>/dev/null || true
	@$(DOCKER_COMPOSE) rm -f redis 2>/dev/null || true
	@echo "$(GREEN)✓ Redis removed$(NC)"

.PHONY: teardown-correlation
teardown-correlation: ## Stop and remove Correlation Engine
	@echo "$(YELLOW)→ Stopping Correlation Engine...$(NC)"
	@$(DOCKER_COMPOSE) stop correlation-engine 2>/dev/null || true
	@$(DOCKER_COMPOSE) rm -f correlation-engine 2>/dev/null || true
	@echo "$(GREEN)✓ Correlation Engine removed$(NC)"

.PHONY: teardown-gateway
teardown-gateway: ## Stop and remove OTel Gateway
	@echo "$(YELLOW)→ Stopping OTel Gateway...$(NC)"
	@$(DOCKER_COMPOSE) stop otel-gateway 2>/dev/null || true
	@$(DOCKER_COMPOSE) rm -f otel-gateway 2>/dev/null || true
	@echo "$(GREEN)✓ Gateway removed$(NC)"

.PHONY: teardown-observability
teardown-observability: ## Stop and remove observability stack
	@echo "$(YELLOW)→ Stopping Observability Stack...$(NC)"
	@$(DOCKER_COMPOSE) stop grafana loki tempo prometheus pyroscope 2>/dev/null || true
	@$(DOCKER_COMPOSE) rm -f grafana loki tempo prometheus pyroscope 2>/dev/null || true
	@echo "$(GREEN)✓ Observability stack removed$(NC)"

.PHONY: teardown-network
teardown-network: ## Remove Docker network
	@echo "$(YELLOW)→ Removing observability network...$(NC)"
	@docker network rm observability 2>/dev/null || true
	@echo "$(GREEN)✓ Network removed$(NC)"

.PHONY: teardown-all
teardown-all: ## Complete teardown (keeps volumes)
	@echo "$(RED)→ Complete teardown (preserving data)...$(NC)"
	@$(MAKE) teardown-frontend
	@$(MAKE) teardown-sense-apps
	@$(MAKE) teardown-correlation
	@$(MAKE) teardown-redis
	@$(MAKE) teardown-gateway
	@$(MAKE) teardown-observability
	@$(MAKE) teardown-network
	@echo "$(GREEN)✓ Complete teardown finished$(NC)"
	@echo "$(YELLOW)Data preserved in Docker volumes$(NC)"

.PHONY: teardown-purge
teardown-purge: teardown-all ## Complete teardown + remove volumes
	@echo "$(RED)⚠️  WARNING: Removing all data volumes$(NC)"
	@read -p "Continue? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	@echo "$(YELLOW)→ Removing volumes...$(NC)"
	@docker volume rm $$(docker volume ls -q | grep -E 'grafana-data|loki-data|tempo-data|prometheus-data|pyroscope-data|redis-data|seca-db') 2>/dev/null || true
	@echo "$(GREEN)✓ All data removed$(NC)"

# ============================================
# Rollback Targets
# ============================================

##@ Rollback & Recovery

.PHONY: rollback-backup
rollback-backup: ## Create backup before changes
	@echo "$(YELLOW)→ Creating backup...$(NC)"
	@mkdir -p $(BACKUP_DIR)
	@docker-compose ps > $(BACKUP_DIR)/service-status.txt
	@docker volume ls > $(BACKUP_DIR)/volumes.txt
	@docker network ls > $(BACKUP_DIR)/networks.txt
	@cp docker-compose.yml $(BACKUP_DIR)/
	@cp Makefile $(BACKUP_DIR)/
	@cp -r correlation-engine/.env $(BACKUP_DIR)/ 2>/dev/null || true
	@echo "$(GREEN)✓ Backup created: $(BACKUP_DIR)$(NC)"

.PHONY: rollback-correlation
rollback-correlation: ## Rollback correlation engine to previous version
	@echo "$(YELLOW)→ Rolling back Correlation Engine...$(NC)"
	@$(DOCKER_COMPOSE) stop correlation-engine
	@$(DOCKER_COMPOSE) rm -f correlation-engine
	@git checkout HEAD~1 -- correlation-engine/ 2>/dev/null || \
		echo "$(YELLOW)Manual rollback required$(NC)"
	@$(DOCKER_COMPOSE) up -d --build correlation-engine
	@echo "$(GREEN)✓ Rollback complete$(NC)"

.PHONY: rollback-redis-disable
rollback-redis-disable: ## Disable Redis and use in-memory state
	@echo "$(YELLOW)→ Disabling Redis state...$(NC)"
	@if [ -f correlation-engine/.env ]; then \
		sed -i 's/USE_REDIS_STATE=true/USE_REDIS_STATE=false/' correlation-engine/.env; \
		echo "$(GREEN)  ✓ Redis disabled in .env$(NC)"; \
	fi
	@$(DOCKER_COMPOSE) restart correlation-engine
	@echo "$(GREEN)✓ Rolled back to in-memory state$(NC)"

.PHONY: rollback-restore-volumes
rollback-restore-volumes: ## Restore volumes from backup
	@echo "$(RED)⚠️  This will restore data from backup$(NC)"
	@read -p "Backup directory timestamp (YYYYMMDD_HHMMSS): " timestamp && \
		if [ -d "backups/$$timestamp" ]; then \
			echo "$(YELLOW)→ Restoring from backups/$$timestamp...$(NC)"; \
			$(MAKE) teardown-all; \
			cp backups/$$timestamp/docker-compose.yml .; \
			cp backups/$$timestamp/.env correlation-engine/ 2>/dev/null || true; \
			$(MAKE) setup-all; \
			echo "$(GREEN)✓ Restore complete$(NC)"; \
		else \
			echo "$(RED)✗ Backup not found$(NC)"; \
		fi

# ============================================
# Health Checks
# ============================================

##@ Health & Monitoring

.PHONY: health-observability
health-observability: ## Health check for observability stack
	@echo "$(YELLOW)Observability Stack:$(NC)"
	@curl -sf http://localhost:8443/api/health >/dev/null 2>&1 && \
		echo "$(GREEN)  ✓ Grafana$(NC)" || echo "$(RED)  ✗ Grafana$(NC)"
	@curl -sf http://localhost:3100/ready >/dev/null 2>&1 && \
		echo "$(GREEN)  ✓ Loki$(NC)" || echo "$(RED)  ✗ Loki$(NC)"
	@curl -sf http://localhost:9000/ready >/dev/null 2>&1 && \
		echo "$(GREEN)  ✓ Tempo$(NC)" || echo "$(RED)  ✗ Tempo$(NC)"
	@curl -sf http://localhost:9090/-/healthy >/dev/null 2>&1 && \
		echo "$(GREEN)  ✓ Prometheus$(NC)" || echo "$(RED)  ✗ Prometheus$(NC)"
	@curl -sf http://localhost:4040/healthz >/dev/null 2>&1 && \
		echo "$(GREEN)  ✓ Pyroscope$(NC)" || echo "$(RED)  ✗ Pyroscope$(NC)"

.PHONY: health-correlation
health-correlation: ## Health check for correlation engine
	@echo "$(YELLOW)Correlation Engine:$(NC)"
	@curl -sf http://localhost:8080/health >/dev/null 2>&1 && \
		echo "$(GREEN)  ✓ Healthy$(NC)" || echo "$(RED)  ✗ Unhealthy$(NC)"

.PHONY: health-gateway
health-gateway: ## Health check for OTel gateway
	@echo "$(YELLOW)OTel Gateway:$(NC)"
	@curl -sf http://localhost:13133 >/dev/null 2>&1 && \
		echo "$(GREEN)  ✓ Healthy$(NC)" || echo "$(RED)  ✗ Unhealthy$(NC)"

.PHONY: health-redis
health-redis: ## Health check for Redis
	@echo "$(YELLOW)Redis:$(NC)"
	@docker exec redis redis-cli ping 2>/dev/null | grep -q PONG && \
		echo "$(GREEN)  ✓ Healthy (PONG)$(NC)" || echo "$(RED)  ✗ Unhealthy$(NC)"

.PHONY: health-sense-apps
health-sense-apps: ## Health check for Sense apps
	@echo "$(YELLOW)Sense Apps:$(NC)"
	@curl -sf http://localhost:5001/v1/health >/dev/null 2>&1 && \
		echo "$(GREEN)  ✓ Beorn$(NC)" || echo "$(RED)  ✗ Beorn$(NC)"
	@curl -sf http://localhost:5002/v1/health >/dev/null 2>&1 && \
		echo "$(GREEN)  ✓ Palantir$(NC)" || echo "$(RED)  ✗ Palantir$(NC)"
	@curl -sf http://localhost:5003/arda/health >/dev/null 2>&1 && \
		echo "$(GREEN)  ✓ Arda$(NC)" || echo "$(RED)  ✗ Arda$(NC)"

.PHONY: health-frontend
health-frontend: ## Health check for Frontend UI
	@echo "$(YELLOW)Frontend UI:$(NC)"
	@curl -sf http://localhost:3000 >/dev/null 2>&1 && \
		echo "$(GREEN)  ✓ Healthy$(NC)" || echo "$(RED)  ✗ Unhealthy$(NC)"

.PHONY: health-full
health-full: ## Complete health check (all services)
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(GREEN)Complete Health Check$(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@echo ""
	@$(MAKE) health-observability
	@echo ""
	@$(MAKE) health-gateway
	@echo ""
	@$(MAKE) health-correlation
	@echo ""
	@$(MAKE) health-redis
	@echo ""
	@$(MAKE) health-sense-apps
	@echo ""
	@$(MAKE) health-frontend
	@echo ""

.PHONY: status
status: ## Show all service status
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(GREEN)Service Status$(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@$(DOCKER_COMPOSE) ps

# ============================================
# Horizontal Scaling Targets
# ============================================

##@ Horizontal Scaling

.PHONY: scale-enable-redis
scale-enable-redis: setup-redis ## Enable Redis-based state for scaling
	@echo "$(YELLOW)→ Enabling Redis state management...$(NC)"
	@if [ ! -f correlation-engine/.env ]; then \
		echo "$(RED)✗ correlation-engine/.env not found$(NC)"; \
		echo "Create it with: make scale-create-env"; \
		exit 1; \
	fi
	@grep -q "USE_REDIS_STATE=true" correlation-engine/.env || \
		echo "USE_REDIS_STATE=true" >> correlation-engine/.env
	@grep -q "REDIS_URL=" correlation-engine/.env || \
		echo "REDIS_URL=redis://redis:6379" >> correlation-engine/.env
	@$(DOCKER_COMPOSE) restart correlation-engine
	@sleep 5
	@echo "$(GREEN)✓ Redis state enabled$(NC)"
	@echo "$(YELLOW)Verify in logs:$(NC)"
	@$(DOCKER_COMPOSE) logs correlation-engine | grep -i redis | tail -5

.PHONY: scale-create-env
scale-create-env: ## Create .env for horizontal scaling
	@echo "$(YELLOW)→ Creating correlation-engine/.env...$(NC)"
	@cat > correlation-engine/.env <<'EOF'
# === Horizontal Scaling Configuration ===
USE_REDIS_STATE=true
REDIS_URL=redis://redis:6379
REDIS_MAX_CONNECTIONS=50
REDIS_KEY_PREFIX=corr:
CORRELATION_TTL_SECONDS=3600
MAX_CORRELATION_AGE_HOURS=24

# === Service Configuration ===
PORT=8080
LOG_LEVEL=info
DEPLOYMENT_ENV=dev
CORR_WINDOW_SECONDS=60
MAX_BATCH_SIZE=5000

# === Backend URLs ===
LOKI_URL=http://loki:3100/loki/api/v1/push
TEMPO_GRPC_ENDPOINT=tempo:4317
TEMPO_HTTP_ENDPOINT=http://tempo:4318
PYROSCOPE_SERVER_ADDRESS=http://pyroscope:4040

# === Authentication (optional) ===
ENABLE_BASIC_AUTH=false
BASIC_AUTH_USER=
BASIC_AUTH_PASS=
EOF
	@echo "$(GREEN)✓ .env created$(NC)"
	@echo "$(YELLOW)Edit if needed: vi correlation-engine/.env$(NC)"

.PHONY: scale-up
scale-up: ## Scale correlation engine to N instances (usage: make scale-up N=3)
	@if [ -z "$(N)" ]; then \
		echo "$(RED)Error: N parameter required$(NC)"; \
		echo "Usage: make scale-up N=3"; \
		exit 1; \
	fi
	@echo "$(YELLOW)→ Scaling correlation-engine to $(N) instances...$(NC)"
	@$(DOCKER_COMPOSE) up -d --scale correlation-engine=$(N)
	@sleep 5
	@echo "$(GREEN)✓ Scaled to $(N) instances$(NC)"
	@$(DOCKER_COMPOSE) ps correlation-engine

.PHONY: scale-down
scale-down: ## Scale down to 1 instance
	@echo "$(YELLOW)→ Scaling down to 1 instance...$(NC)"
	@$(DOCKER_COMPOSE) up -d --scale correlation-engine=1
	@echo "$(GREEN)✓ Scaled down$(NC)"

.PHONY: scale-test
scale-test: ## Test horizontal scaling with load
	@echo "$(YELLOW)→ Testing horizontal scaling...$(NC)"
	@echo "Current instances: $$(docker ps | grep correlation-engine | wc -l)"
	@echo "Sending 1000 requests..."
	@for i in {1..1000}; do \
		curl -s -X POST http://localhost:8080/api/logs \
			-H "Content-Type: application/json" \
			-d '{"resource":{"service":"scale-test"},"records":[{"timestamp":"'$$(date -u +%Y-%m-%dT%H:%M:%SZ)'","severity":"INFO","message":"Test $$i"}]}' \
			>/dev/null & \
	done
	@wait
	@echo "$(GREEN)✓ Load test complete$(NC)"
	@echo "Check Redis:"
	@docker exec redis redis-cli DBSIZE

# ============================================
# K6 Load Testing Targets
# ============================================

##@ K6 Load Testing

.PHONY: k6-install
k6-install: ## Install K6 (if not using Docker)
	@echo "$(YELLOW)→ Installing K6...$(NC)"
	@if command -v k6 >/dev/null 2>&1; then \
		echo "$(GREEN)✓ K6 already installed$(NC)"; \
		k6 version; \
	else \
		echo "Installing K6..."; \
		curl https://github.com/grafana/k6/releases/download/v0.47.0/k6-v0.47.0-linux-amd64.tar.gz -L | tar xvz; \
		sudo mv k6-v0.47.0-linux-amd64/k6 /usr/local/bin/; \
		rm -rf k6-v0.47.0-linux-amd64; \
		echo "$(GREEN)✓ K6 installed$(NC)"; \
	fi

.PHONY: k6-test-basic
k6-test-basic: ## Run basic K6 load test
	@echo "$(YELLOW)→ Running basic K6 test...$(NC)"
	@if [ -f k6/load-test-basic.js ]; then \
		k6 run k6/load-test-basic.js; \
	else \
		echo "$(RED)k6/load-test-basic.js not found$(NC)"; \
	fi

.PHONY: k6-test-logs
k6-test-logs: ## Run K6 log ingestion test
	@echo "$(YELLOW)→ Running K6 log test...$(NC)"
	@if [ -f k6/load-test-logs.js ]; then \
		k6 run k6/load-test-logs.js; \
	else \
		echo "$(RED)k6/load-test-logs.js not found$(NC)"; \
	fi

.PHONY: k6-test-stress
k6-test-stress: ## Run K6 stress test (high load)
	@echo "$(YELLOW)→ Running K6 stress test...$(NC)"
	@k6 run --vus 100 --duration 5m k6/load-test-logs.js

.PHONY: k6-test-docker
k6-test-docker: ## Run K6 test in Docker
	@echo "$(YELLOW)→ Running K6 in Docker...$(NC)"
	@docker run --rm -i --network observability \
		-v $(PWD)/k6:/scripts \
		grafana/k6:latest run /scripts/load-test-logs.js

# ============================================
# Debug & Troubleshooting Targets
# ============================================

##@ Debug & Troubleshooting

.PHONY: debug-logs-all
debug-logs-all: ## Show all container logs
	@$(DOCKER_COMPOSE) logs --tail=100 --timestamps

.PHONY: debug-logs-correlation
debug-logs-correlation: ## Debug correlation engine logs
	@echo "$(YELLOW)Correlation Engine Logs (last 100 lines):$(NC)"
	@$(DOCKER_COMPOSE) logs --tail=100 correlation-engine

.PHONY: debug-logs-redis
debug-logs-redis: ## Debug Redis logs
	@echo "$(YELLOW)Redis Logs (last 50 lines):$(NC)"
	@docker logs redis --tail=50

.PHONY: debug-logs-gateway
debug-logs-gateway: ## Debug OTel Gateway logs
	@echo "$(YELLOW)OTel Gateway Logs (last 100 lines):$(NC)"
	@$(DOCKER_COMPOSE) logs --tail=100 otel-gateway

.PHONY: debug-redis-info
debug-redis-info: ## Show Redis info and stats
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(GREEN)Redis Debug Info$(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@echo ""
	@echo "$(YELLOW)Server Info:$(NC)"
	@docker exec redis redis-cli INFO server | grep -E "redis_version|os|uptime"
	@echo ""
	@echo "$(YELLOW)Memory Usage:$(NC)"
	@docker exec redis redis-cli INFO memory | grep -E "used_memory_human|maxmemory"
	@echo ""
	@echo "$(YELLOW)Stats:$(NC)"
	@docker exec redis redis-cli INFO stats | grep -E "total_connections|total_commands"
	@echo ""
	@echo "$(YELLOW)Database Size:$(NC)"
	@docker exec redis redis-cli DBSIZE
	@echo ""
	@echo "$(YELLOW)Sample Keys:$(NC)"
	@docker exec redis redis-cli --scan --pattern 'corr:*' | head -10

.PHONY: debug-redis-monitor
debug-redis-monitor: ## Monitor Redis commands in real-time
	@echo "$(YELLOW)Monitoring Redis (Ctrl+C to stop)...$(NC)"
	@docker exec -it redis redis-cli MONITOR

.PHONY: debug-redis-cli
debug-redis-cli: ## Open Redis CLI
	@echo "$(YELLOW)Opening Redis CLI...$(NC)"
	@docker exec -it redis redis-cli

.PHONY: debug-network
debug-network: ## Debug Docker network
	@echo "$(BLUE)Network Info:$(NC)"
	@docker network inspect observability | jq '.[0] | {Name, Containers}'

.PHONY: debug-ports
debug-ports: ## Show all exposed ports
	@echo "$(BLUE)Exposed Ports:$(NC)"
	@docker ps --format "table {{.Names}}\t{{.Ports}}" | grep -v "^NAMES"

.PHONY: debug-env-correlation
debug-env-correlation: ## Show correlation engine environment
	@echo "$(BLUE)Correlation Engine Environment:$(NC)"
	@docker exec correlation-engine env | grep -E "REDIS|USE_|PORT|LOG_LEVEL" | sort

.PHONY: debug-disk-usage
debug-disk-usage: ## Show Docker disk usage
	@echo "$(BLUE)Docker Disk Usage:$(NC)"
	@docker system df -v

.PHONY: debug-container-stats
debug-container-stats: ## Show container resource usage
	@echo "$(BLUE)Container Resource Usage:$(NC)"
	@docker stats --no-stream

.PHONY: troubleshoot-correlation
troubleshoot-correlation: ## Troubleshoot correlation engine issues
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(GREEN)Troubleshooting Correlation Engine$(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@echo ""
	@echo "$(YELLOW)1. Container Status:$(NC)"
	@docker ps -a | grep correlation-engine || echo "  Not running"
	@echo ""
	@echo "$(YELLOW)2. Health Check:$(NC)"
	@curl -sf http://localhost:8080/health && echo " ✓ Healthy" || echo " ✗ Unhealthy"
	@echo ""
	@echo "$(YELLOW)3. Recent Logs (errors):$(NC)"
	@$(DOCKER_COMPOSE) logs --tail=50 correlation-engine | grep -i error || echo "  No errors"
	@echo ""
	@echo "$(YELLOW)4. Environment:$(NC)"
	@docker exec correlation-engine env | grep -E "REDIS|LOKI|TEMPO" || echo "  Cannot access"
	@echo ""
	@echo "$(YELLOW)5. Network:$(NC)"
	@docker exec correlation-engine ping -c 1 redis 2>/dev/null && echo "  ✓ Can reach Redis" || echo "  ✗ Cannot reach Redis"

.PHONY: troubleshoot-redis
troubleshoot-redis: ## Troubleshoot Redis issues
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(GREEN)Troubleshooting Redis$(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@echo ""
	@echo "$(YELLOW)1. Container Status:$(NC)"
	@docker ps -a | grep redis || echo "  Not running"
	@echo ""
	@echo "$(YELLOW)2. Ping Test:$(NC)"
	@docker exec redis redis-cli ping 2>/dev/null || echo "  Cannot connect"
	@echo ""
	@echo "$(YELLOW)3. Memory:$(NC)"
	@docker exec redis redis-cli INFO memory | grep used_memory_human || echo "  Cannot get memory info"
	@echo ""
	@echo "$(YELLOW)4. Slow Log:$(NC)"
	@docker exec redis redis-cli SLOWLOG GET 5 || echo "  Cannot get slow log"

.PHONY: troubleshoot-network
troubleshoot-network: ## Troubleshoot network issues
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(GREEN)Troubleshooting Network$(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@echo ""
	@echo "$(YELLOW)1. Network Exists:$(NC)"
	@docker network ls | grep observability && echo "  ✓ Network exists" || echo "  ✗ Network missing"
	@echo ""
	@echo "$(YELLOW)2. Connected Containers:$(NC)"
	@docker network inspect observability 2>/dev/null | jq '.[0].Containers | keys[]' || echo "  Cannot inspect"
	@echo ""
	@echo "$(YELLOW)3. Port Conflicts:$(NC)"
	@for port in 3000 8080 8443 9090 6379; do \
		lsof -Pi :$$port -sTCP:LISTEN -t >/dev/null 2>&1 && echo "  Port $$port: IN USE" || echo "  Port $$port: free"; \
	done

.PHONY: fix-permissions
fix-permissions: ## Fix file permissions
	@echo "$(YELLOW)→ Fixing permissions...$(NC)"
	@chmod +x scripts/*.sh 2>/dev/null || true
	@chmod +x ops/*.sh 2>/dev/null || true
	@chmod 644 k6/*.js 2>/dev/null || true
	@echo "$(GREEN)✓ Permissions fixed$(NC)"

.PHONY: fix-network
fix-network: ## Fix network issues
	@echo "$(YELLOW)→ Fixing network...$(NC)"
	@$(MAKE) teardown-network
	@sleep 2
	@$(MAKE) setup-network
	@echo "$(GREEN)✓ Network recreated$(NC)"

.PHONY: fix-redis
fix-redis: ## Fix Redis issues
	@echo "$(YELLOW)→ Fixing Redis...$(NC)"
	@$(DOCKER_COMPOSE) stop redis
	@$(DOCKER_COMPOSE) rm -f redis
	@docker volume rm redis-data 2>/dev/null || true
	@$(DOCKER_COMPOSE) up -d redis
	@sleep 3
	@docker exec redis redis-cli ping
	@echo "$(GREEN)✓ Redis restarted$(NC)"

# ============================================
# Logging Targets
# ============================================

##@ Logging

.PHONY: logs-all
logs-all: ## Tail all service logs
	@$(DOCKER_COMPOSE) logs -f --tail=100

.PHONY: logs-correlation
logs-correlation: ## Tail correlation engine logs
	@$(DOCKER_COMPOSE) logs -f --tail=100 correlation-engine

.PHONY: logs-redis
logs-redis: ## Tail Redis logs
	@docker logs -f redis

.PHONY: logs-gateway
logs-gateway: ## Tail OTel Gateway logs
	@$(DOCKER_COMPOSE) logs -f --tail=100 otel-gateway

.PHONY: logs-grafana
logs-grafana: ## Tail Grafana logs
	@$(DOCKER_COMPOSE) logs -f --tail=100 grafana

.PHONY: logs-sense
logs-sense: ## Tail Sense apps logs
	@$(DOCKER_COMPOSE) logs -f --tail=50 beorn palantir arda

.PHONY: logs-errors
logs-errors: ## Show only error logs
	@$(DOCKER_COMPOSE) logs --tail=200 | grep -i error

.PHONY: logs-export
logs-export: ## Export logs to file
	@mkdir -p logs-export
	@echo "$(YELLOW)→ Exporting logs...$(NC)"
	@$(DOCKER_COMPOSE) logs --no-color > logs-export/all-logs-$(TIMESTAMP).log
	@$(DOCKER_COMPOSE) logs correlation-engine --no-color > logs-export/correlation-$(TIMESTAMP).log
	@docker logs redis --no-color > logs-export/redis-$(TIMESTAMP).log 2>&1
	@echo "$(GREEN)✓ Logs exported to logs-export/$(NC)"

# ============================================
# Testing Targets
# ============================================

##@ Testing

.PHONY: test-traffic
test-traffic: ## Generate test traffic (logs + traces)
	@echo "$(YELLOW)→ Generating test traffic...$(NC)"
	@$(MAKE) test-logs
	@$(MAKE) test-traces
	@echo "$(GREEN)✓ Test traffic generated$(NC)"

.PHONY: test-logs
test-logs: ## Send test logs
	@echo "$(YELLOW)→ Sending test logs...$(NC)"
	@for i in {1..10}; do \
		curl -s -X POST http://localhost:8080/api/logs \
			-H "Content-Type: application/json" \
			-d '{"resource":{"service":"test","host":"localhost"},"records":[{"timestamp":"'$$(date -u +%Y-%m-%dT%H:%M:%SZ)'","severity":"INFO","message":"Test log $$i","trace_id":"'$$(openssl rand -hex 16)'"}]}' \
			>/dev/null; \
	done
	@echo "$(GREEN)✓ Sent 10 test logs$(NC)"

.PHONY: test-traces
test-traces: ## Generate test traces from Sense apps
	@echo "$(YELLOW)→ Generating test traces...$(NC)"
	@curl -s http://localhost:5001/api/test >/dev/null 2>&1 && echo "  ✓ Beorn" || echo "  ✗ Beorn not available"
	@curl -s http://localhost:5002/api/test >/dev/null 2>&1 && echo "  ✓ Palantir" || echo "  ✗ Palantir not available"
	@curl -s http://localhost:5003/api/test >/dev/null 2>&1 && echo "  ✓ Arda" || echo "  ✗ Arda not available"

.PHONY: test-correlation-api
test-correlation-api: ## Test correlation engine API endpoints
	@echo "$(BLUE)Testing Correlation API:$(NC)"
	@echo ""
	@echo "$(YELLOW)Health:$(NC)"
	@curl -s http://localhost:8080/health | jq '.'
	@echo ""
	@echo "$(YELLOW)Recent Correlations:$(NC)"
	@curl -s http://localhost:8080/api/correlations?limit=5 | jq '.'

.PHONY: test-redis-connection
test-redis-connection: ## Test Redis connection
	@echo "$(YELLOW)→ Testing Redis connection...$(NC)"
	@docker exec redis redis-cli ping && echo "$(GREEN)✓ Redis PONG$(NC)"
	@docker exec redis redis-cli SET test:key "test-value" >/dev/null
	@docker exec redis redis-cli GET test:key
	@docker exec redis redis-cli DEL test:key >/dev/null
	@echo "$(GREEN)✓ Redis connection working$(NC)"

# ============================================
# Utility Targets
# ============================================

##@ Utilities

.PHONY: shell-correlation
shell-correlation: ## Open shell in correlation engine
	@docker exec -it correlation-engine /bin/bash

.PHONY: shell-redis
shell-redis: ## Open shell in Redis container
	@docker exec -it redis /bin/sh

.PHONY: shell-grafana
shell-grafana: ## Open shell in Grafana
	@docker exec -it grafana /bin/sh

.PHONY: open-grafana
open-grafana: ## Open Grafana in browser
	@echo "$(GREEN)Opening Grafana...$(NC)"
	@command -v xdg-open >/dev/null 2>&1 && xdg-open http://159.56.4.94:8443 || \
		echo "Visit: http://159.56.4.94:8443"

.PHONY: open-frontend
open-frontend: ## Open Frontend UI in browser
	@echo "$(GREEN)Opening Frontend...$(NC)"
	@command -v xdg-open >/dev/null 2>&1 && xdg-open http://localhost:3000 || \
		echo "Visit: http://localhost:3000"

.PHONY: clean-logs
clean-logs: ## Clean old log files
	@echo "$(YELLOW)→ Cleaning logs...$(NC)"
	@rm -rf logs-export/*.log
	@find sense-apps/*/logs -name "*.log" -mtime +7 -delete 2>/dev/null || true
	@echo "$(GREEN)✓ Logs cleaned$(NC)"

.PHONY: prune
prune: ## Remove unused Docker resources
	@echo "$(YELLOW)→ Pruning Docker resources...$(NC)"
	@docker system prune -f
	@echo "$(GREEN)✓ Prune complete$(NC)"

.PHONY: show-urls
show-urls: ## Show all service URLs
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(GREEN)Service URLs$(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@echo ""
	@echo "$(YELLOW)User Interfaces:$(NC)"
	@echo "  Frontend:    http://localhost:3000"
	@echo "  Grafana:     http://159.56.4.94:8443 (admin/admin)"
	@echo "  Prometheus:  http://159.56.4.94:9090"
	@echo "  Pyroscope:   http://localhost:4040"
	@echo ""
	@echo "$(YELLOW)APIs:$(NC)"
	@echo "  Correlation: http://159.56.4.94:8080"
	@echo "  API Docs:    http://159.56.4.94:8080/docs"
	@echo "  Health:      http://159.56.4.94:8080/health"
	@echo "  Metrics:     http://159.56.4.94:8080/metrics"
	@echo ""
	@echo "$(YELLOW)Sense Apps:$(NC)"
	@echo "  Beorn:       http://localhost:5001"
	@echo "  Palantir:    http://localhost:5002"
	@echo "  Arda:        http://localhost:5003"
	@echo ""
	@echo "$(YELLOW)Backends:$(NC)"
	@echo "  Loki:        http://localhost:3100"
	@echo "  Tempo:       http://localhost:9000"
	@echo "  Redis:       localhost:6379"
	@echo "  OTLP HTTP:   http://localhost:55681"
	@echo ""

.PHONY: version
version: ## Show versions of all components
	@echo "$(BLUE)Component Versions:$(NC)"
	@echo "Docker: $$(docker --version)"
	@echo "Docker Compose: $$($(DOCKER_COMPOSE) version --short)"
	@echo "Grafana: $$(docker exec grafana grafana-cli --version 2>/dev/null || echo 'Not running')"
	@echo "Redis: $$(docker exec redis redis-cli --version 2>/dev/null || echo 'Not running')"

# ============================================
# Quick Aliases
# ============================================

.PHONY: up
up: setup-all ## Alias for setup-all

.PHONY: down
down: teardown-all ## Alias for teardown-all

.PHONY: restart
restart: teardown-all setup-all ## Restart all services

.PHONY: health
health: health-full ## Alias for health-full

.PHONY: logs
logs: logs-all ## Alias for logs-all

# ============================================
# End of Makefile
# ============================================
