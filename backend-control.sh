#!/bin/bash
# THE_BOT Backend Control Script
# Manages backend Daphne process on production server

SERVER="mg@5.129.249.206"
PROJECT_DIR="/opt/THE_BOT_platform"
BACKEND_DIR="$PROJECT_DIR/backend"

case "$1" in
  status)
    echo "=== Backend Status ==="
    ssh "$SERVER" "ps aux | grep -E 'daphne|config.asgi' | grep -v grep || echo 'Not running'"
    echo ""
    echo "Port 8000 status:"
    ssh "$SERVER" "ss -tlnp 2>/dev/null | grep 8000 || echo 'Port 8000 not listening'"
    echo ""
    echo "Recent logs (last 15 lines):"
    ssh "$SERVER" "tail -15 /tmp/daphne.log"
    ;;

  stop)
    echo "Stopping backend..."
    ssh "$SERVER" "pkill -f 'daphne.*config.asgi' 2>/dev/null && echo 'Backend stopped' || echo 'Backend not running'"
    sleep 1
    ;;

  start)
    echo "Starting backend..."
    ssh "$SERVER" "cd /opt/THE_BOT_platform/backend && source ../venv/bin/activate && nohup daphne -b 0.0.0.0 -p 8000 -v 2 config.asgi:application > /tmp/daphne.log 2>&1 &"
    sleep 2
    echo "Backend started. Checking status..."
    ssh "$SERVER" "ps aux | grep -E 'daphne|config.asgi' | grep -v grep || echo 'Failed to start'"
    ;;

  restart)
    echo "Restarting backend..."
    $0 stop
    sleep 2
    $0 start
    ;;

  logs)
    echo "=== Backend Logs (live) ==="
    echo "Press Ctrl+C to stop"
    ssh "$SERVER" "tail -f /tmp/daphne.log"
    ;;

  logs-last)
    echo "=== Last 50 lines of backend logs ==="
    ssh "$SERVER" "tail -50 /tmp/daphne.log"
    ;;

  test)
    echo "Testing backend connectivity..."
    echo "1. Testing localhost:8000..."
    ssh "$SERVER" "curl -s -m 3 http://localhost:8000/api/system/health/live/ >/dev/null 2>&1 && echo '  OK' || echo '  FAILED'"
    echo ""
    echo "2. Testing external IP (5.129.249.206:8000)..."
    ssh "$SERVER" "curl -s -m 3 http://5.129.249.206:8000/api/system/health/live/ >/dev/null 2>&1 && echo '  OK' || echo '  FAILED'"
    ;;

  *)
    echo "THE_BOT Backend Control Script"
    echo ""
    echo "Usage: $0 {status|start|stop|restart|logs|logs-last|test}"
    echo ""
    echo "Commands:"
    echo "  status    - Show backend status"
    echo "  start     - Start backend"
    echo "  stop      - Stop backend"
    echo "  restart   - Restart backend"
    echo "  logs      - View live logs (Ctrl+C to exit)"
    echo "  logs-last - View last 50 log lines"
    echo "  test      - Test backend connectivity"
    echo ""
    exit 1
    ;;
esac
