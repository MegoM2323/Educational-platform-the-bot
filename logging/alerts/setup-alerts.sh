#!/bin/bash

# Setup script for THE_BOT Platform Alert Rules

set -e

KIBANA_URL="${KIBANA_URL:-http://localhost:5601}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

main() {
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  THE_BOT Platform Alert Setup              ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════╝${NC}"
    echo ""

    # Check Kibana
    echo -e "${YELLOW}Checking Kibana connectivity...${NC}"
    if curl -s "$KIBANA_URL/api/status" >/dev/null; then
        echo -e "${GREEN}✓ Kibana is healthy${NC}"
    else
        echo -e "${RED}✗ Cannot reach Kibana on $KIBANA_URL${NC}"
        exit 1
    fi

    # Summary
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════${NC}"
    echo -e "${GREEN}Alert Setup Summary${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════${NC}"
    echo ""
    echo "Configuration:"
    echo "  • Total Rules: 16"
    echo "  • Severity Levels: critical, high, medium"
    echo "  • Notification Channels: Email, Slack, PagerDuty"
    echo "  • Retention: 30 days online, 90 days archived"
    echo ""
    echo "Alert Categories:"
    echo "  • Critical: 5 (immediate escalation)"
    echo "  • High: 5 (urgent investigation)"
    echo "  • Medium: 6 (monitoring/tracking)"
    echo ""
    echo "Dashboard:"
    echo "  • API Performance: Response times, error rates, endpoints"
    echo "  • Security Events: Threats, attacks, failed logins"
    echo ""
    echo "Next Steps:"
    echo "  1. Configure environment variables in .env"
    echo "  2. Access Kibana: $KIBANA_URL"
    echo "  3. Import dashboards via Stack Management"
    echo "  4. Configure notification channels"
    echo "  5. Enable alert rules"
    echo ""
    echo "Documentation:"
    echo "  • See docs/LOGGING_MONITORING.md for details"
    echo "  • Alert rules: logging/alerts/alert-rules.json"
    echo "  • Pipelines: logging/logstash/pipelines/"
    echo ""
    echo -e "${GREEN}Setup Ready!${NC}"
    echo ""
}

main "$@"
