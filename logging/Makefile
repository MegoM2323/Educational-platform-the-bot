.PHONY: help start stop restart logs test clean build

# Variables
DOCKER_COMPOSE := docker-compose
PYTHON := python3
LOGSTASH_HOST := localhost
LOGSTASH_PORT := 5000
ELASTICSEARCH_URL := http://localhost:9200
KIBANA_URL := http://localhost:5601

help:
	@echo "ELK Stack Management Commands"
	@echo "============================="
	@echo ""
	@echo "Infrastructure:"
	@echo "  make start              Start all ELK services"
	@echo "  make stop               Stop all services"
	@echo "  make restart            Restart all services"
	@echo "  make status             Show service status"
	@echo "  make logs               View all service logs"
	@echo "  make logs-service       View logs for specific service (SERVICE=logstash)"
	@echo ""
	@echo "Testing & Verification:"
	@echo "  make test               Run comprehensive tests"
	@echo "  make test-es            Test Elasticsearch connectivity"
	@echo "  make test-kibana        Test Kibana connectivity"
	@echo "  make test-logstash      Test Logstash pipeline"
	@echo "  make test-logs          Test log collection"
	@echo ""
	@echo "Monitoring:"
	@echo "  make health             Check cluster health"
	@echo "  make stats              Show cluster statistics"
	@echo "  make indices            List all indices"
	@echo "  make disk-usage         Show disk usage by index"
	@echo "  make memory             Check memory usage"
	@echo ""
	@echo "Management:"
	@echo "  make create-backup      Create snapshot backup"
	@echo "  make list-backups       List available backups"
	@echo "  make delete-old         Delete indices older than 30 days"
	@echo "  make cleanup            Clean all data and containers"
	@echo ""
	@echo "Configuration:"
	@echo "  make build              Build custom Docker images"
	@echo "  make validate           Validate configurations"
	@echo "  make setup-auth         Setup authentication (production)"
	@echo ""

.PHONY: start
start:
	@echo "Starting ELK Stack services..."
	$(DOCKER_COMPOSE) up -d
	@echo "Waiting for services to be ready..."
	@sleep 10
	@$(MAKE) health

.PHONY: stop
stop:
	@echo "Stopping ELK Stack services..."
	$(DOCKER_COMPOSE) down

.PHONY: restart
restart: stop start

.PHONY: status
status:
	@echo "Service Status:"
	$(DOCKER_COMPOSE) ps

.PHONY: logs
logs:
	$(DOCKER_COMPOSE) logs -f

.PHONY: logs-service
logs-service:
	@if [ -z "$(SERVICE)" ]; then \
		echo "Usage: make logs-service SERVICE=<service>"; \
		echo "Available services: elasticsearch, logstash, kibana, filebeat, metricbeat"; \
	else \
		$(DOCKER_COMPOSE) logs -f $(SERVICE); \
	fi

.PHONY: test
test:
	@echo "Running ELK Stack tests..."
	$(PYTHON) test_elk_stack.py

.PHONY: test-es
test-es:
	@echo "Testing Elasticsearch connectivity..."
	@curl -s $(ELASTICSEARCH_URL) | python3 -m json.tool
	@echo "\nCluster health:"
	@curl -s $(ELASTICSEARCH_URL)/_cluster/health | python3 -m json.tool

.PHONY: test-kibana
test-kibana:
	@echo "Testing Kibana connectivity..."
	@curl -s $(KIBANA_URL)/api/status | python3 -m json.tool

.PHONY: test-logstash
test-logstash:
	@echo "Testing Logstash pipeline..."
	@curl -s http://localhost:9600/ | python3 -m json.tool

.PHONY: test-logs
test-logs:
	@echo "Testing log collection..."
	@curl -s "$(ELASTICSEARCH_URL)/thebot-logs-*/_search?size=1" | python3 -m json.tool

.PHONY: health
health:
	@echo "Elasticsearch Cluster Health:"
	@curl -s $(ELASTICSEARCH_URL)/_cluster/health | python3 -m json.tool

.PHONY: stats
stats:
	@echo "Elasticsearch Cluster Stats:"
	@curl -s $(ELASTICSEARCH_URL)/_cluster/stats | python3 -m json.tool | head -50

.PHONY: indices
indices:
	@echo "All Indices:"
	@curl -s "$(ELASTICSEARCH_URL)/_cat/indices?v&s=i"

.PHONY: disk-usage
disk-usage:
	@echo "Disk Usage by Index:"
	@curl -s "$(ELASTICSEARCH_URL)/_cat/indices?v&s=store.size:desc&h=index,store.size,p,r"

.PHONY: memory
memory:
	@echo "Memory Usage:"
	@curl -s "$(ELASTICSEARCH_URL)/_nodes/stats/jvm" | python3 -m json.tool | grep -A 5 "heap_used"

.PHONY: create-backup
create-backup:
	@echo "Creating snapshot backup..."
	@DATE=$$(date +%Y%m%d_%H%M%S); \
	curl -X PUT "$(ELASTICSEARCH_URL)/_snapshot/backup/logs-backup-$$DATE" \
		-H 'Content-Type: application/json' \
		-d '{"indices":"thebot-*","ignore_unavailable":true,"include_global_state":false}'; \
	echo "\nSnapshot created: logs-backup-$$DATE"

.PHONY: list-backups
list-backups:
	@echo "Available Snapshots:"
	@curl -s "$(ELASTICSEARCH_URL)/_snapshot/backup/_all" | python3 -m json.tool

.PHONY: delete-old
delete-old:
	@echo "Deleting indices older than 30 days..."
	@DATE=$$(date -d '30 days ago' +%Y.%m.%d); \
	curl -X DELETE "$(ELASTICSEARCH_URL)/thebot-logs-$$DATE" && \
	echo "Deleted indices from $$DATE and earlier"

.PHONY: cleanup
cleanup:
	@echo "WARNING: This will delete all logs and containers!"
	@read -p "Are you sure? (yes/no): " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		$(DOCKER_COMPOSE) down -v; \
		rm -rf data/*; \
		echo "Cleanup completed"; \
	else \
		echo "Cleanup cancelled"; \
	fi

.PHONY: build
build:
	@echo "Building custom Docker images..."
	$(DOCKER_COMPOSE) build

.PHONY: validate
validate:
	@echo "Validating Logstash configuration..."
	@docker-compose exec logstash logstash -f /usr/share/logstash/pipeline/logstash.conf --syntax-check || true
	@echo ""
	@echo "Validating docker-compose.yml..."
	@$(DOCKER_COMPOSE) config > /dev/null && echo "✓ docker-compose.yml is valid" || echo "✗ Invalid configuration"

.PHONY: setup-auth
setup-auth:
	@echo "Setting up authentication (production)..."
	@$(DOCKER_COMPOSE) exec elasticsearch \
		elasticsearch-setup-passwords auto -b -u elastic

.PHONY: send-test-log
send-test-log:
	@echo "Sending test log to Logstash..."
	@echo '{"message":"Test log entry","service":"test-runner","level":"INFO"}' | \
	nc -q 1 $(LOGSTASH_HOST) $(LOGSTASH_PORT)
	@echo "Test log sent. Check Kibana in a moment."

.PHONY: create-index-pattern
create-index-pattern:
	@echo "Creating index pattern in Kibana..."
	@curl -X POST "$(KIBANA_URL)/api/index_patterns/index_pattern" \
		-H "kbn-xsrf: true" \
		-H "Content-Type: application/json" \
		-d '{"index_pattern":"thebot-logs-*","timeFieldName":"@timestamp","title":"THE_BOT Logs"}' || \
		echo "Pattern may already exist"

.PHONY: open-kibana
open-kibana:
	@echo "Opening Kibana in browser..."
	@command -v xdg-open > /dev/null && xdg-open $(KIBANA_URL) || \
	command -v open > /dev/null && open $(KIBANA_URL) || \
	echo "Open $(KIBANA_URL) in your browser"

.PHONY: tail-logs
tail-logs:
	@echo "Tailing Django logs..."
	@tail -f ../backend/logs/django.log 2>/dev/null || echo "Logs not available"

.PHONY: show-config
show-config:
	@echo "Current Configuration:"
	@echo "====================="
	@echo "Elasticsearch URL: $(ELASTICSEARCH_URL)"
	@echo "Kibana URL: $(KIBANA_URL)"
	@echo "Logstash: $(LOGSTASH_HOST):$(LOGSTASH_PORT)"
	@echo ""
	@echo "Environment files:"
	@ls -la .env* 2>/dev/null | grep -v "^total" || echo "No .env files found"
