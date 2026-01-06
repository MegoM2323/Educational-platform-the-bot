#!/bin/bash
set -e

# Direct deployment without Docker (FAST)
# This script deploys THE_BOT directly to production server

SERVER="mg@5.129.249.206"
PROJECT_PATH="/opt/THE_BOT_platform"
LOCAL_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== THE_BOT Direct Deployment (No Docker) ==="
echo "Server: $SERVER"
echo "Project path: $PROJECT_PATH"
echo ""

# Step 1: Sync code to server
echo "[1/6] Syncing code to server..."
rsync -avz --delete \
  --exclude '.git' \
  --exclude '__pycache__' \
  --exclude '.pytest_cache' \
  --exclude '.mypy_cache' \
  --exclude 'venv' \
  --exclude '.venv' \
  --exclude 'node_modules' \
  --exclude '.env.local' \
  --exclude '.env' \
  --exclude '.env.production.native' \
  --exclude 'dist' \
  --exclude 'build' \
  "$LOCAL_PATH/backend" \
  "$SERVER:$PROJECT_PATH/"

echo "✓ Code synced"
echo ""

# Step 2: Install Python dependencies
echo "[2/6] Installing Python dependencies..."
ssh "$SERVER" bash << 'EOF'
cd /opt/THE_BOT_platform
python3.12 -m venv venv --upgrade-deps
. venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r backend/requirements.txt
EOF
echo "✓ Dependencies installed"
echo ""

# Step 3: Setup environment
echo "[3/6] Setting up environment..."
ssh "$SERVER" bash << 'EOF'
cd /opt/THE_BOT_platform/backend

# Create .env if not exists
if [ ! -f .env ]; then
  cat > .env << 'ENVEOF'
DB_ENGINE=django.db.backends.postgresql
DB_NAME=thebot_db
DB_USER=thebot_user
DB_PASSWORD=thebot_secure_password_change_in_production
DB_HOST=localhost
DB_PORT=5432
DB_SSLMODE=disable

REDIS_HOST=localhost
REDIS_PORT=6379

ALLOWED_HOSTS=the-bot.ru,www.the-bot.ru,5.129.249.206,localhost,127.0.0.1

ENVIRONMENT=production
DEBUG=False
SECRET_KEY=change-this-in-production-to-random-value
ENVEOF
fi
EOF
echo "✓ Environment configured"
echo ""

# Step 4: Run migrations
echo "[4/6] Running database migrations..."
ssh "$SERVER" bash << 'EOF'
cd /opt/THE_BOT_platform/backend
. /opt/THE_BOT_platform/venv/bin/activate
python manage.py migrate --noinput 2>&1 || echo "⚠ Migrations may have connection issues (DB might not be running yet)"
python manage.py collectstatic --noinput || true
EOF
echo "✓ Migrations applied (or deferred)"
echo ""

# Step 5: Create systemd service file (manual setup required)
echo "[5/6] Creating systemd service..."

ssh "$SERVER" bash << 'SERVICEEOF'
# Create service file in /tmp
cat > /tmp/thebot-backend.service << 'SVCEOF'
[Unit]
Description=THE_BOT Backend (Daphne ASGI)
After=network.target

[Service]
Type=simple
User=mg
WorkingDirectory=/opt/THE_BOT_platform/backend
Environment="PATH=/opt/THE_BOT_platform/venv/bin"
EnvironmentFile=/opt/THE_BOT_platform/backend/.env
ExecStart=/opt/THE_BOT_platform/venv/bin/daphne -b 0.0.0.0 -p 8000 -v 2 config.asgi:application
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
KillMode=mixed

[Install]
WantedBy=multi-user.target
SVCEOF

echo "Service file created at /tmp/thebot-backend.service"
echo "To install with sudo, run:"
echo "  sudo cp /tmp/thebot-backend.service /etc/systemd/system/"
echo "  sudo systemctl daemon-reload"
SERVICEEOF

echo "✓ Service file template created"
echo ""

# Step 6: Start backend using supervisor or direct process
echo "[6/6] Starting THE_BOT backend service..."
ssh "$SERVER" bash << 'EOF'
# Kill any existing daphne processes
pkill -f "daphne.*config.asgi" || true
sleep 1

cd /opt/THE_BOT_platform/backend
. /opt/THE_BOT_platform/venv/bin/activate

# Start daphne in background with logging
echo "Starting Daphne on 0.0.0.0:8000..."
nohup daphne -b 0.0.0.0 -p 8000 -v 2 config.asgi:application > /tmp/daphne.log 2>&1 &
DAPHNE_PID=$!
sleep 2

# Check if process is still running
if kill -0 $DAPHNE_PID 2>/dev/null; then
  echo "✓ Daphne started successfully (PID: $DAPHNE_PID)"
  echo "Logs: tail -f /tmp/daphne.log"
else
  echo "✗ Daphne failed to start. Checking logs..."
  tail -20 /tmp/daphne.log
  exit 1
fi
EOF
echo "✓ Backend started"
echo ""

# Verify
echo "=== Verification ==="
sleep 3
echo "Checking if backend is responding on port 8000..."
ssh "$SERVER" bash << 'VERIFYEOF' || echo "⚠ Backend not responding yet (might still be starting)"
# Try to connect to backend
for i in {1..5}; do
  if curl -s -m 3 http://localhost:8000/api/system/health/live/ 2>/dev/null | head -5; then
    echo "✓ Backend is responding"
    break
  else
    echo "  Attempt $i/5: backend not ready yet..."
    sleep 2
  fi
done

# Show process info
echo ""
echo "Backend process status:"
ps aux | grep -E "daphne|config.asgi" | grep -v grep || echo "No daphne process found"

# Check port
echo ""
echo "Port 8000 status:"
ss -tlnp 2>/dev/null | grep 8000 || echo "Port 8000 not in LISTEN state"
VERIFYEOF

echo ""
echo "=== DEPLOYMENT COMPLETE ==="
echo "Backend running at: http://5.129.249.206:8000"
echo ""
echo "Useful commands:"
echo "  View logs:       ssh $SERVER 'tail -f /tmp/daphne.log'"
echo "  Check process:   ssh $SERVER 'ps aux | grep daphne'"
echo "  Stop backend:    ssh $SERVER 'pkill -f \"daphne.*config.asgi\"'"
echo "  Check port:      ssh $SERVER 'ss -tlnp | grep 8000'"
echo ""
echo "To make systemd service (requires sudo password setup):"
echo "  1. SSH to server: ssh $SERVER"
echo "  2. Install service: sudo cp /tmp/thebot-backend.service /etc/systemd/system/"
echo "  3. Enable service: sudo systemctl daemon-reload && sudo systemctl enable thebot-backend"
echo "  4. Start service: sudo systemctl start thebot-backend"
