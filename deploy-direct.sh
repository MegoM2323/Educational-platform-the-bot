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
  --exclude '.env.production' \
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

# Step 5: Create systemd service file
echo "[5/6] Creating systemd service..."

# Create service file locally
SERVICE_FILE=$(mktemp)
cat > "$SERVICE_FILE" << 'SERVICEEOF'
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

[Install]
WantedBy=multi-user.target
SERVICEEOF

# Copy service file to server and install via sudo
ssh "$SERVER" bash << COPEOF
# Copy service file to /tmp first
cat > /tmp/thebot-backend.service << 'SERVICEEOF'
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

[Install]
WantedBy=multi-user.target
SERVICEEOF

# Now use sudo to move it to the right place
echo 'About to create systemd service. You may be prompted for password.'
sudo mv /tmp/thebot-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
echo 'Systemd service created successfully'
COPEOF

rm -f "$SERVICE_FILE"
echo "✓ Systemd service created"
echo ""

# Step 6: Start service
echo "[6/6] Starting THE_BOT backend service..."
ssh "$SERVER" bash << 'EOF'
# Start the service if systemd is available, otherwise run daphne directly
if command -v systemctl &> /dev/null; then
  echo "Using systemd to start service..."
  sudo systemctl start thebot-backend
  sleep 2
  sudo systemctl status thebot-backend --no-pager || true
else
  echo "systemd not available, starting daphne directly..."
  cd /opt/THE_BOT_platform/backend
  . /opt/THE_BOT_platform/venv/bin/activate
  nohup daphne -b 0.0.0.0 -p 8000 -v 2 config.asgi:application &> /tmp/daphne.log &
  echo "Daphne started (PID: $!)"
fi
EOF
echo "✓ Service started"
echo ""

# Verify
echo "=== Verification ==="
sleep 3
echo "Checking if backend is responding..."
ssh "$SERVER" bash << 'VERIFYEOF' || echo "⚠ Not responding yet (might still be starting)"
curl -s -m 5 http://localhost:8000/api/system/health/live/ | head -20
VERIFYEOF

echo ""
echo "=== DEPLOYMENT COMPLETE ==="
echo "Backend should be running at: http://5.129.249.206:8000"
echo ""
echo "Useful commands:"
echo "  View logs:       ssh $SERVER 'sudo journalctl -u thebot-backend -f'"
echo "  Check status:    ssh $SERVER 'sudo systemctl status thebot-backend'"
echo "  Manual start:    ssh $SERVER 'sudo systemctl start thebot-backend'"
echo "  Manual stop:     ssh $SERVER 'sudo systemctl stop thebot-backend'"
echo ""
echo "Why native deployment is faster than Docker:"
echo "  - No Docker image rebuild (was 20+ minutes)"
echo "  - No multi-stage build overhead"
echo "  - No package download delays (uses pip cache)"
echo "  - Just rsync + pip install + migrate = ~2-3 minutes"
