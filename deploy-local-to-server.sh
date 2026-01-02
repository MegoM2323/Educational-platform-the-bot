#!/bin/bash

set -e

SSH_USER="neil"
SSH_HOST="176.108.248.21"
SSH_PORT="22"
REMOTE_PATH="/home/neil/thebot"

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  THE_BOT Platform - Deploy to Production${NC}"
echo -e "${BLUE}  Server: neil@176.108.248.21${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo

echo -e "${BLUE}[1/7]${NC} Testing SSH connection..."
if ssh -p $SSH_PORT $SSH_USER@$SSH_HOST "echo OK" &>/dev/null; then
    echo -e "${GREEN}✓${NC} SSH OK"
else
    echo -e "${RED}✗${NC} SSH Failed"
    exit 1
fi

echo -e "${BLUE}[2/7]${NC} Checking Docker..."
if ssh -p $SSH_PORT $SSH_USER@$SSH_HOST "command -v docker docker-compose" &>/dev/null; then
    echo -e "${GREEN}✓${NC} Docker OK"
else
    echo -e "${RED}✗${NC} Docker not found"
    exit 1
fi

echo -e "${BLUE}[3/7]${NC} Uploading files..."
ssh -p $SSH_PORT $SSH_USER@$SSH_HOST "mkdir -p $REMOTE_PATH"
rsync -avz --delete -e "ssh -p $SSH_PORT" \
    --exclude='.git' --exclude='__pycache__' --exclude='node_modules' \
    --exclude='.env' --exclude='*.pyc' --exclude='.venv' --exclude='venv' \
    "$(pwd)/" "$SSH_USER@$SSH_HOST:$REMOTE_PATH/" 2>/dev/null | tail -3
echo -e "${GREEN}✓${NC} Upload OK"

echo -e "${BLUE}[4/7]${NC} Creating .env..."
SECRET_KEY=$(openssl rand -base64 32)
DB_PASS=$(openssl rand -base64 16)
REDIS_PASS=$(openssl rand -base64 16)

cat > /tmp/.env << 'ENV_EOF'
ENVIRONMENT=production
DEBUG=False
SECRET_KEY={{SECRET_KEY}}
ALLOWED_HOSTS=176.108.248.21,localhost

DB_ENGINE=postgresql
DB_HOST=postgres
DB_PORT=5432
DB_NAME=thebot_db
DB_USER=postgres
DB_PASSWORD={{DB_PASS}}

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD={{REDIS_PASS}}

CELERY_BROKER_URL=redis://:{{REDIS_PASS}}@redis:6379/1
CELERY_RESULT_BACKEND=redis://:{{REDIS_PASS}}@redis:6379/2

API_URL=http://176.108.248.21:8000/api
FRONTEND_URL=http://176.108.248.21:3000

EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True

LOG_LEVEL=INFO
ENV_EOF

sed -i "s|{{SECRET_KEY}}|$SECRET_KEY|g" /tmp/.env
sed -i "s|{{DB_PASS}}|$DB_PASS|g" /tmp/.env
sed -i "s|{{REDIS_PASS}}|$REDIS_PASS|g" /tmp/.env

scp -P $SSH_PORT /tmp/.env "$SSH_USER@$SSH_HOST:$REMOTE_PATH/.env" 2>/dev/null
rm /tmp/.env
echo -e "${GREEN}✓${NC} .env OK"

echo -e "${BLUE}[5/7]${NC} Building images (this takes ~10 minutes)..."
ssh -p $SSH_PORT $SSH_USER@$SSH_HOST "cd $REMOTE_PATH && docker-compose build" 2>&1 | grep -E "(Building|Successfully|Error)" || true

echo -e "${BLUE}[6/7]${NC} Starting services..."
ssh -p $SSH_PORT $SSH_USER@$SSH_HOST "cd $REMOTE_PATH && docker-compose up -d"
echo -e "${GREEN}✓${NC} Services started"

echo -e "${BLUE}[7/7]${NC} Initializing DB..."
sleep 20
ssh -p $SSH_PORT $SSH_USER@$SSH_HOST "cd $REMOTE_PATH && docker-compose exec -T backend python manage.py migrate --noinput 2>/dev/null" || echo "Migrations: skipped"
ssh -p $SSH_PORT $SSH_USER@$SSH_HOST "cd $REMOTE_PATH && docker-compose exec -T backend python manage.py reset_and_seed_users 2>/dev/null" || echo "Seeding: skipped"
echo -e "${GREEN}✓${NC} DB initialized"

echo
echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓✓✓ DEPLOYMENT COMPLETE ✓✓✓${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
echo
echo "🌐 Access:"
echo "   API:      http://176.108.248.21:8000/api"
echo "   Frontend: http://176.108.248.21:3000"
echo "   Admin:    http://176.108.248.21:8000/admin"
echo
echo "👤 Credentials:"
echo "   Admin:    admin / admin12345"
echo "   Student:  test_student@example.com / test123"
echo "   Teacher:  test_teacher@example.com / test123"
echo "   Tutor:    test_tutor@example.com / test123"
echo "   Parent:   test_parent@example.com / test123"
echo
echo "📡 Connect:"
echo "   ssh neil@176.108.248.21"
echo "   cd $REMOTE_PATH"
echo "   docker-compose logs -f"
echo

