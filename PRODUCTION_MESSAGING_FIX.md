# Production Messaging Fix - Deployment Guide

## Обзор

Данный релиз устраняет критические проблемы в системе обмена сообщениями THE_BOT Platform:
- Race conditions при создании чатов
- Отсутствие родительских участников в форумных чатах
- Проблемы сериализации сообщений
- WebSocket переподключение и маршрутизация
- Production конфигурация Redis Channel Layer

## Изменения

### Backend - Chat Creation (signals.py)
**Проблема:** Race conditions при одновременных запросах создания чатов
**Решение:**
- Использование `get_or_create()` вместо `filter().first() + create()`
- Atomic операции с `transaction.atomic()`
- `bulk_create()` с `ignore_conflicts=True` для участников
- Добавлены родительские участники в FORUM_SUBJECT и FORUM_TUTOR чаты
- Новый signal handler `sync_parent_participants` для M2M синхронизации

**Файлы:** `backend/chat/signals.py`

### Backend - Message Serialization (consumers.py)
**Проблема:** Sender получает только `message_id`, recipients получают полный объект
**Решение:**
- Sender теперь получает полный объект сообщения с sender data
- Унифицированный формат response для ChatConsumer и GeneralChatConsumer
- Frontend может делать optimistic UI updates без дополнительных API запросов

**Файлы:** `backend/chat/consumers.py`

### Backend - WebSocket Routing (routing.py, consumers.py)
**Проблема:** Frontend подключается к `/ws/chat` без room_id, backend требует `/ws/chat/<room_id>/`
**Решение:**
- Добавлен fallback pattern в routing.py: `re_path(r'^ws/chat/$', ...)`
- Flexible room_id extraction в `connect()`:
  1. URL path parameter: `/ws/chat/123/`
  2. Query string: `/ws/chat?room_id=123`
  3. Fallback: первый доступный chat room для user
- Новый метод `get_first_available_room()` для автоматического выбора

**Файлы:** `backend/chat/routing.py`, `backend/chat/consumers.py`

### Backend - Redis Channel Layer (settings.py)
**Проблема:** Hardcoded `localhost` не работает в Docker контекстах
**Решение:**
- Redis Channel Layer использует `REDIS_HOST` и `REDIS_PORT` env переменные
- Fallback на `127.0.0.1:6379` если переменные не установлены
- Добавлены `capacity: 1500` и `expiry: 10` для production stability

**Файлы:** `backend/config/settings.py`, `.env.production`

### Frontend - WebSocket Reconnection (chatSocket.ts)
**Проблема:** Нет автоматического переподключения при network issues
**Решение:**
- Exponential backoff: 1s → 2s → 4s → 8s → 16s → 30s (max)
- Max 5 reconnect attempts перед уведомлением user
- State tracking: `lastRoomId`, `lastToken` для восстановления соединения
- User notifications: `connection_lost`, `connection_established` events

**Файлы:** `frontend/src/integrations/websocket/chatSocket.ts`

### Frontend - WebSocket Room Switching (chatSocket.ts, useChat.ts)
**Проблема:** WebSocket URL не содержит room_id, сообщения идут в неправильный чат
**Решение:**
- `connect(roomId, token)` теперь использует `/ws/chat/{roomId}/` URL
- `disconnect()` → `connect(newRoomId)` при смене чата
- Backward compatible fallback на `/ws/chat` если roomId не указан

**Файлы:** `frontend/src/integrations/websocket/chatSocket.ts`, `frontend/src/hooks/useChat.ts`

### Deployment - Daphne ASGI Server
**Добавлено:**
- Systemd service unit: `deploy/systemd/daphne.service`
- Integration в `safe-deploy-native.sh`:
  - Автоматическое создание daphne.service если не существует
  - Restart daphne вместе с backend services
  - Health checks: port 8001, WebSocket endpoint HTTP 426

**Файлы:** `deploy/systemd/daphne.service`, `scripts/deployment/safe-deploy-native.sh`

---

## Pre-Deployment Checklist

### 1. Backup Database
```bash
sudo -u postgres pg_dump thebot_db > /home/mg/backups/thebot_db_$(date +%Y%m%d_%H%M%S).sql
```

### 2. Check Current Services Status
```bash
sudo systemctl status thebot-backend thebot-celery-worker thebot-celery-beat
# Daphne может не существовать - это нормально, скрипт создаст
sudo systemctl status thebot-daphne || echo "Daphne service not found - will be created"
```

### 3. Verify Redis and PostgreSQL Running
```bash
sudo systemctl status redis-server postgresql
```

### 4. Check Disk Space
```bash
df -h /home/mg
# Должно быть минимум 5GB свободного места
```

### 5. Verify Git Status
```bash
cd /home/mg/THE_BOT_platform
git fetch origin main
git status
# Если есть uncommitted changes - stash or commit them
```

---

## Deployment Steps

### Метод 1: Используя safe-deploy-native.sh (Рекомендуется)

```bash
# 1. SSH в production server
ssh mg@176.108.248.21

# 2. Dry-run для проверки (без изменений)
cd /home/mg/THE_BOT_platform
./scripts/deployment/safe-deploy-native.sh --dry-run

# 3. Полный deployment
./scripts/deployment/safe-deploy-native.sh

# Скрипт выполнит:
# - Phase 0: Проверка daphne.service, создание если нужно
# - Phase 1-5: Standard deployment (git pull, migrations, collectstatic)
# - Phase 6: Restart backend + daphne + celery
# - Phase 7: Verification (backend, daphne port 8001, WebSocket endpoint)
```

### Метод 2: Manual Deployment

```bash
# 1. SSH в production
ssh mg@176.108.248.21
cd /home/mg/THE_BOT_platform

# 2. Pull latest code
git fetch origin main
git merge origin/main

# 3. Activate virtualenv
source /home/mg/venv/bin/activate

# 4. Install dependencies (если были изменения)
pip install -r requirements.txt

# 5. Run migrations
cd backend
python manage.py migrate

# 6. Collect static files
python manage.py collectstatic --noinput

# 7. Create Daphne systemd service (если не существует)
sudo cp /home/mg/THE_BOT_platform/deploy/systemd/daphne.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable daphne

# 8. Restart all services
sudo systemctl restart thebot-backend
sudo systemctl restart thebot-daphne
sudo systemctl restart thebot-celery-worker
sudo systemctl restart thebot-celery-beat

# 9. Check service status
sudo systemctl status thebot-backend thebot-daphne thebot-celery-worker thebot-celery-beat
```

---

## Post-Deployment Verification

### 1. Services Running
```bash
sudo systemctl status thebot-backend thebot-daphne thebot-celery-worker thebot-celery-beat

# Все должны быть в состоянии "active (running)"
```

### 2. Daphne WebSocket Endpoint
```bash
# Проверка порта 8001
nc -z localhost 8001 && echo "Port 8001 OPEN" || echo "Port 8001 CLOSED"

# Проверка WebSocket endpoint (должен вернуть HTTP 426 Upgrade Required)
curl -I http://localhost:8001/ws/chat/1/
# Expected: HTTP/1.1 426 Upgrade Required
```

### 3. Redis Channel Layer Connection
```bash
# Проверка Redis доступен
redis-cli ping
# Expected: PONG

# Проверка Django может подключиться к Redis Channel Layer
cd /home/mg/THE_BOT_platform/backend
source /home/mg/venv/bin/activate
python manage.py shell << EOF
from channels.layers import get_channel_layer
import asyncio
channel_layer = get_channel_layer()
asyncio.run(channel_layer.send("test_channel", {"type": "test.message"}))
print("Channel Layer OK")
EOF
```

### 4. Chat Creation Test
```bash
# В Django shell
cd /home/mg/THE_BOT_platform/backend
source /home/mg/venv/bin/activate
python manage.py shell << EOF
from accounts.models import StudentProfile, TeacherProfile
from materials.models import Subject, SubjectEnrollment

# Get test student and teacher
student = StudentProfile.objects.filter(user__role='STUDENT', user__is_active=True).first()
teacher = TeacherProfile.objects.filter(user__role='TEACHER', user__is_active=True).first()
subject = Subject.objects.first()

if student and teacher and subject:
    # Create enrollment (should trigger chat creation signal)
    enrollment, created = SubjectEnrollment.objects.get_or_create(
        student=student.user,
        teacher=teacher.user,
        subject=subject,
        defaults={'is_active': True}
    )
    print(f"Enrollment: {enrollment.id}, Created: {created}")

    # Check FORUM_SUBJECT chat created
    from chat.models import ChatRoom, ChatParticipant
    forum_chats = ChatRoom.objects.filter(enrollment=enrollment, type='FORUM_SUBJECT')
    print(f"FORUM_SUBJECT chats: {forum_chats.count()}")

    if forum_chats.exists():
        chat = forum_chats.first()
        participants = ChatParticipant.objects.filter(room=chat).select_related('user')
        print(f"Participants: {[p.user.full_name for p in participants]}")

        # Check parent is participant
        if student.parent:
            parent_in_chat = participants.filter(user=student.parent).exists()
            print(f"Parent in chat: {parent_in_chat}")
else:
    print("Missing test data: student, teacher, or subject")
EOF
```

### 5. WebSocket Connection Test (from Frontend)
```bash
# В браузере DevTools Console на the-bot.ru
const ws = new WebSocket('wss://the-bot.ru/ws/chat/1/?token=YOUR_TOKEN');
ws.onopen = () => console.log('Connected');
ws.onmessage = (e) => console.log('Message:', e.data);
ws.onerror = (e) => console.error('Error:', e);

# Send test message
ws.send(JSON.stringify({
    type: 'chat_message',
    message: 'Test message',
    room_id: 1
}));
```

### 6. Check Logs for Errors
```bash
# Backend logs
journalctl -u thebot-backend -f --lines=100

# Daphne logs
journalctl -u thebot-daphne -f --lines=100

# Celery logs
journalctl -u thebot-celery-worker -f --lines=100

# Должны отсутствовать errors связанные с:
# - Redis connection
# - Channel Layer
# - WebSocket routing
# - Chat creation signals
```

---

## Rollback Plan

### Если deployment не удался:

#### 1. Rollback Code
```bash
cd /home/mego/THE_BOT_platform
git log --oneline -5  # Найти предыдущий коммит
git reset --hard <PREVIOUS_COMMIT_HASH>
```

#### 2. Rollback Database (если были migrations)
```bash
cd backend
source /home/mg/venv/bin/activate

# Проверить текущие migrations
python manage.py showmigrations chat

# Откатить до предыдущей миграции
python manage.py migrate chat <PREVIOUS_MIGRATION_NUMBER>
```

#### 3. Restart Services
```bash
sudo systemctl restart thebot-backend thebot-daphne thebot-celery-worker thebot-celery-beat
```

#### 4. Restore Database from Backup (если критично)
```bash
sudo systemctl stop thebot-backend thebot-daphne thebot-celery-worker

sudo -u postgres psql << EOF
DROP DATABASE thebot_db;
CREATE DATABASE thebot_db OWNER mg;
EOF

sudo -u postgres psql thebot_db < /home/mg/backups/thebot_db_TIMESTAMP.sql

sudo systemctl start thebot-backend thebot-daphne thebot-celery-worker
```

---

## Troubleshooting

### Problem: Daphne не запускается
**Симптомы:**
```bash
sudo systemctl status thebot-daphne
# Status: failed
```

**Решение:**
```bash
# 1. Проверить логи
journalctl -u thebot-daphne -n 50

# 2. Проверить права на файлы
ls -la /home/mg/THE_BOT_platform/backend

# 3. Проверить virtualenv
/home/mg/venv/bin/daphne --version

# 4. Проверить конфигурацию
cat /etc/systemd/system/thebot-daphne.service

# 5. Ручной запуск для debugging
cd /home/mg/THE_BOT_platform/backend
source /home/mg/venv/bin/activate
daphne -b 0.0.0.0 -p 8001 config.asgi:application
# Смотреть вывод для ошибок
```

### Problem: WebSocket connections fail с 403 Forbidden
**Симптомы:**
- Frontend console: `WebSocket connection failed: 403 Forbidden`

**Решение:**
```bash
# 1. Проверить CORS и CSRF settings
cd /home/mg/THE_BOT_platform/backend
source /home/mg/venv/bin/activate
python manage.py shell << EOF
from django.conf import settings
print("ALLOWED_HOSTS:", settings.ALLOWED_HOSTS)
print("CSRF_TRUSTED_ORIGINS:", settings.CSRF_TRUSTED_ORIGINS)
print("CORS_ALLOWED_ORIGINS:", settings.CORS_ALLOWED_ORIGINS)
EOF

# 2. Проверить Nginx proxy configuration
sudo nginx -t
sudo systemctl reload nginx

# 3. Проверить authentication token
# В frontend DevTools localStorage должен содержать token
```

### Problem: Messages не доставляются recipient
**Симптомы:**
- Sender видит сообщение, recipient не получает

**Решение:**
```bash
# 1. Проверить Redis Channel Layer
redis-cli
> KEYS channel*
> MONITOR
# Отправить сообщение и смотреть логи Redis

# 2. Проверить ChatConsumer routing
cd /home/mg/THE_BOT_platform/backend
grep -n "self.room_group_name" chat/consumers.py

# 3. Проверить participants в ChatRoom
python manage.py shell << EOF
from chat.models import ChatRoom, ChatParticipant
room = ChatRoom.objects.get(id=ROOM_ID)
participants = ChatParticipant.objects.filter(room=room).select_related('user')
print([p.user.full_name for p in participants])
EOF
```

### Problem: Race condition - duplicate chats created
**Симптомы:**
- В БД несколько FORUM_SUBJECT чатов для одного enrollment

**Решение:**
```bash
# 1. Найти дубликаты
cd /home/mg/THE_BOT_platform/backend
source /home/mg/venv/bin/activate
python manage.py shell << EOF
from chat.models import ChatRoom
from collections import Counter

# Найти enrollment с несколькими чатами
enrollment_counts = Counter(
    ChatRoom.objects.filter(type='FORUM_SUBJECT').values_list('enrollment_id', flat=True)
)
duplicates = {k: v for k, v in enrollment_counts.items() if v > 1}
print(f"Duplicate enrollments: {duplicates}")
EOF

# 2. Удалить дубликаты (оставить только первый)
python manage.py shell << EOF
from chat.models import ChatRoom

for enrollment_id, count in duplicates.items():
    chats = ChatRoom.objects.filter(enrollment_id=enrollment_id, type='FORUM_SUBJECT').order_by('id')
    # Оставить первый, удалить остальные
    for chat in chats[1:]:
        print(f"Deleting duplicate chat {chat.id}")
        chat.delete()
EOF
```

### Problem: Parent не видит student's chats
**Симптомы:**
- ParentProfile.user is set, но parent не в participants

**Решение:**
```bash
# 1. Вручную синхронизировать
cd /home/mg/THE_BOT_platform/backend
source /home/mg/venv/bin/activate
python manage.py shell << EOF
from accounts.models import StudentProfile
from chat.models import ChatRoom, ChatParticipant

student_profiles = StudentProfile.objects.filter(parent__isnull=False).select_related('parent')

for student_profile in student_profiles:
    student = student_profile.user
    parent = student_profile.parent

    # Найти все чаты студента
    rooms = ChatRoom.objects.filter(participants__user=student)

    for room in rooms:
        # Добавить parent если нет
        if not room.participants.filter(id=parent.id).exists():
            room.participants.add(parent)
            ChatParticipant.objects.get_or_create(user=parent, room=room)
            print(f"Added parent {parent.id} to room {room.id}")
EOF

# 2. Проверить signal работает
# Обновить StudentProfile (должно триггернуть sync_parent_participants)
python manage.py shell << EOF
from accounts.models import StudentProfile

student_profile = StudentProfile.objects.filter(parent__isnull=False).first()
student_profile.save()  # Triggers post_save signal
EOF
```

---

## Performance Monitoring

### Redis Channel Layer Metrics
```bash
# В production мониторить Redis memory usage
redis-cli info memory | grep used_memory_human

# Проверить channel expiry (должны удаляться после 10 секунд)
redis-cli
> KEYS asgi*
> TTL asgi:channel_name
```

### WebSocket Connections
```bash
# Количество активных WebSocket соединений
sudo netstat -an | grep :8001 | grep ESTABLISHED | wc -l

# Daphne memory usage
ps aux | grep daphne
```

### Database Chat Statistics
```bash
cd /home/mg/THE_BOT_platform/backend
source /home/mg/venv/bin/activate
python manage.py shell << EOF
from chat.models import ChatRoom, ChatMessage, ChatParticipant
from collections import Counter

print(f"Total rooms: {ChatRoom.objects.count()}")
print(f"Total messages: {ChatMessage.objects.count()}")
print(f"Total participants: {ChatParticipant.objects.count()}")

room_types = Counter(ChatRoom.objects.values_list('type', flat=True))
print(f"Room types: {dict(room_types)}")
EOF
```

---

## Summary

**Deployment time:** ~10-15 минут (с проверками)

**Downtime:** ~2-3 минуты (restart services)

**Risk level:** LOW
- No breaking schema changes
- Backward compatible WebSocket routing
- Atomic signal operations
- Automatic rollback в safe-deploy-native.sh

**Success criteria:**
1. ✅ All services running (backend, daphne, celery)
2. ✅ Daphne port 8001 accessible
3. ✅ WebSocket endpoint returns HTTP 426
4. ✅ Chat creation creates FORUM_SUBJECT + participants (including parent)
5. ✅ Messages delivered to all participants
6. ✅ WebSocket auto-reconnects after network drop
7. ✅ No errors in journalctl logs
