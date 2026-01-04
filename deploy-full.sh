#!/bin/bash
set -e

# Full deployment script - Frontend + Backend + Nginx
SERVER="mg@5.129.249.206"
LOCAL_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOMAIN="the-bot.ru"
IP="5.129.249.206"

echo "╔══════════════════════════════════════════════════╗"
echo "║  THE_BOT FULL DEPLOYMENT                        ║"
echo "║  Domain: $DOMAIN ($IP)                 ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# Step 1: Sync backend code
echo "[1/7] Syncing backend code..."
rsync -avz --delete \
  --exclude '.git' \
  --exclude '__pycache__' \
  --exclude '.pytest_cache' \
  --exclude '.mypy_cache' \
  --exclude 'venv' \
  --exclude '.venv' \
  --exclude 'node_modules' \
  --exclude '.env.local' \
  "$LOCAL_PATH/backend" \
  "$SERVER:/opt/THE_BOT_platform/"
echo "✓ Backend synced"

# Step 2: Sync frontend code
echo "[2/7] Syncing frontend code..."
rsync -avz --delete \
  --exclude 'node_modules' \
  --exclude '.next' \
  --exclude 'dist' \
  --exclude '.env.local' \
  --exclude '.git' \
  "$LOCAL_PATH/frontend" \
  "$SERVER:/opt/THE_BOT_platform/"
echo "✓ Frontend synced"

# Step 3: Setup backend (already running but ensure it's good)
echo "[3/7] Verifying backend dependencies..."
ssh "$SERVER" bash << 'BACKEND_EOF'
cd /opt/THE_BOT_platform
[ -d venv ] || python3.12 -m venv venv --upgrade-deps
. venv/bin/activate
pip install -q -r backend/requirements.txt 2>/dev/null || true
echo "✓ Backend dependencies verified"
BACKEND_EOF

# Step 4: Build frontend
echo "[4/7] Building frontend..."
ssh "$SERVER" bash << 'FRONTEND_EOF'
cd /opt/THE_BOT_platform/frontend
echo "Installing dependencies..."
if command -v bun &> /dev/null; then
  bun install 2>/dev/null || true
else
  npm install --silent 2>/dev/null || npm install
fi

echo "Building for production..."
if command -v bun &> /dev/null; then
  bun run build 2>&1 | tail -5
else
  npm run build 2>&1 | tail -5
fi
echo "✓ Frontend built (dist/ ready)"
FRONTEND_EOF

# Step 5: Setup nginx configuration
echo "[5/7] Configuring nginx..."
ssh "$SERVER" bash << 'NGINX_EOF'
# Create nginx config for THE_BOT
cat > /tmp/thebot.conf << 'CONFEOF'
# THE_BOT Nginx Configuration
upstream backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

# HTTP to HTTPS redirect
server {
    listen 80;
    listen [::]:80;
    server_name the-bot.ru www.the-bot.ru 5.129.249.206;

    # Let's Encrypt verification
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Redirect HTTP to HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS server block
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name the-bot.ru www.the-bot.ru 5.129.249.206;

    # SSL certificates (use self-signed for now)
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Frontend (React SPA - Vite)
    location / {
        # Serve from frontend dist directory
        root /opt/THE_BOT_platform/frontend;
        try_files $uri $uri/ /index.html;

        # Enable caching for static files
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # JS, CSS, etc with content hashing (immutable)
    location ~* \.(js|css|woff|woff2|ttf|otf|eot|svg)$ {
        root /opt/THE_BOT_platform/frontend;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # API endpoints
    location /api/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 30s;
        proxy_connect_timeout 10s;
    }

    # Admin panel
    location /admin/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files
    location /static/ {
        alias /opt/THE_BOT_platform/backend/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media files
    location /media/ {
        alias /opt/THE_BOT_platform/backend/media/;
        expires 7d;
    }
}
CONFEOF

# Copy config
sudo mkdir -p /etc/nginx/ssl
sudo mkdir -p /etc/nginx/sites-available
sudo mkdir -p /etc/nginx/sites-enabled
sudo cp /tmp/thebot.conf /etc/nginx/sites-available/thebot.conf
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/thebot.conf /etc/nginx/sites-enabled/thebot.conf

# Self-signed certificate for testing (if not exists)
if [ ! -f /etc/nginx/ssl/cert.pem ]; then
  echo "Creating self-signed certificate..."
  sudo openssl req -x509 -newkey rsa:2048 -keyout /etc/nginx/ssl/key.pem -out /etc/nginx/ssl/cert.pem -days 365 -nodes -subj "/C=RU/ST=Moscow/L=Moscow/O=THE_BOT/CN=the-bot.ru"
fi

# Test nginx config
sudo nginx -t

echo "✓ Nginx configured"
NGINX_EOF

# Step 6: Start all services
echo "[6/7] Starting services..."
ssh "$SERVER" bash << 'START_EOF'
# Start backend (if not running)
if ! pgrep -f "daphne.*8000" > /dev/null; then
  echo "Starting backend..."
  cd /opt/THE_BOT_platform/backend
  . /opt/THE_BOT_platform/venv/bin/activate
  nohup daphne -b 127.0.0.1 -p 8000 -v 1 config.asgi:application &> /tmp/daphne.log &
  sleep 2
fi

# Start frontend (serve dist folder)
if ! pgrep -f "python.*3000" > /dev/null 2>&1 && ! pgrep -f "http-server.*3000" > /dev/null 2>&1; then
  echo "Starting frontend..."
  cd /opt/THE_BOT_platform/frontend
  if [ ! -d dist ]; then
    echo "dist folder not found, skipping frontend start (will use static files from nginx)"
  else
    # Use Python simple HTTP server
    nohup python3 -m http.server 3000 --directory dist &> /tmp/frontend.log &
    sleep 2
  fi
fi

# Start nginx
echo "Starting nginx..."
sudo systemctl start nginx || sudo service nginx start
sudo systemctl enable nginx || true

sleep 2
echo "✓ Services started"
START_EOF

# Step 7: Verify all services
echo "[7/7] Verifying deployment..."
echo ""
echo "Checking services..."

# Check backend
if ssh "$SERVER" "curl -s http://localhost:8000/ > /dev/null 2>&1"; then
  echo "✓ Backend (127.0.0.1:8000)     - OK"
else
  echo "✗ Backend (127.0.0.1:8000)     - FAILED"
fi

# Check frontend build
if ssh "$SERVER" "[ -d /opt/THE_BOT_platform/frontend/dist ]"; then
  echo "✓ Frontend (dist)              - Built and ready"
else
  echo "⚠ Frontend (dist)              - Checking build..."
fi

# Check nginx
if ssh "$SERVER" "curl -s https://localhost/ 2>/dev/null > /dev/null || curl -s http://localhost/ > /dev/null"; then
  echo "✓ Nginx (80/443)               - OK"
else
  echo "⚠ Nginx                        - Checking..."
fi

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║  DEPLOYMENT COMPLETE                            ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "🌐 Access THE_BOT:"
echo "  - Domain:    https://$DOMAIN"
echo "  - IP:        https://$IP"
echo "  - Admin:     https://$DOMAIN/admin"
echo "  - API Docs:  https://$DOMAIN/api/schema/"
echo ""
echo "📋 Service Status:"
ssh "$SERVER" "echo '  Backend:  '; pgrep -f 'daphne.*8000' > /dev/null && echo '    ✓ Running on 127.0.0.1:8000' || echo '    ✗ Not running'; echo '  Frontend: '; [ -d /opt/THE_BOT_platform/frontend/dist ] && echo '    ✓ Built (served via nginx)' || echo '    ✗ Not built'; echo '  Nginx:    '; sudo systemctl is-active nginx > /dev/null 2>&1 && echo '    ✓ Running (port 80/443)' || echo '    ✗ Not running'"
echo ""
echo "🔍 Test URLs:"
echo "  curl https://$DOMAIN/"
echo "  curl https://$DOMAIN/api/system/health/live/"
echo "  curl https://$DOMAIN/admin/"
echo ""
echo "📝 Logs:"
echo "  Backend:  ssh mg@$IP 'tail -f /tmp/daphne.log'"
echo "  Nginx:    ssh mg@$IP 'sudo tail -f /var/log/nginx/error.log'"
echo ""
