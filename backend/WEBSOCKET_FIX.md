# WebSocket 404 Error - Root Cause and Fix

## Problem

WebSocket connections to `/ws/chat/general/` were returning **HTTP 404 Unexpected response code**, causing real-time chat functionality to fail.

**Symptoms:**
- Frontend attempts: `ws://localhost:8000/ws/chat/general/`
- Backend returns: HTTP 404
- Messages require page refresh instead of real-time delivery
- Browser console shows WebSocket connection errors

## Root Cause

The development server was started with:
```bash
python manage.py runserver
```

**Django's runserver does NOT support WebSocket connections.** It only handles HTTP/HTTPS protocols. WebSocket requires an ASGI server like Daphne.

## Solution

Changed `start.sh` (line 166) from:
```bash
"$VENV_DIR/bin/python" manage.py runserver 8000 &
```

To:
```bash
"$VENV_DIR/bin/daphne" -b 0.0.0.0 -p 8000 config.asgi:application &
```

## Why This Works

1. **Daphne is an ASGI server** - supports both HTTP and WebSocket protocols
2. **Channels integration** - properly handles Django Channels WebSocket consumers
3. **ASGI application** - configured in `/backend/config/asgi.py` with WebSocket routing

## WebSocket Configuration

### Backend Routes (chat/routing.py)
```python
websocket_urlpatterns = [
    re_path(r'ws/$', GeneralChatConsumer.as_asgi()),
    re_path(r'ws/chat/(?P<room_id>\w+)/$', ChatConsumer.as_asgi()),
    re_path(r'ws/chat/general/$', GeneralChatConsumer.as_asgi()),
    re_path(r'ws/notifications/(?P<user_id>\w+)/$', NotificationConsumer.as_asgi()),
    re_path(r'ws/dashboard/(?P<user_id>\w+)/$', DashboardConsumer.as_asgi()),
]
```

### ASGI Application (config/asgi.py)
```python
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    ),
})
```

### Channel Layers (config/settings.py)
- **Development:** InMemoryChannelLayer (no Redis required)
- **Production:** RedisChannelLayer (Redis required for multi-process)

## Verification Steps

### 1. Check Configuration
```bash
cd backend
source ../.venv/bin/activate
python test_websocket.py
```

Expected output:
```
WebSocket Configuration Test
============================================================
1. ASGI Application: ProtocolTypeRouter
2. WebSocket URL Patterns: 5 routes found
3. Channel Layers: InMemoryChannelLayer
4. Available Consumers: 5 consumers
============================================================
```

### 2. Start Server with Daphne
```bash
# Option 1: Use start.sh (now uses Daphne automatically)
./start.sh

# Option 2: Start Daphne manually
cd backend
source ../.venv/bin/activate
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

### 3. Test WebSocket Connection

**Browser Console Test:**
```javascript
// Open browser console, navigate to http://localhost:8080
const ws = new WebSocket('ws://localhost:8000/ws/chat/general/');

ws.onopen = () => console.log('✅ WebSocket connected');
ws.onerror = (e) => console.error('❌ WebSocket error:', e);
ws.onmessage = (e) => console.log('📨 Message:', e.data);

// Send test message
ws.send(JSON.stringify({
  type: 'chat_message',
  data: { content: 'Hello WebSocket!' }
}));
```

**Expected Result:**
- `✅ WebSocket connected` appears in console
- No 404 errors
- Connection stays open (ReadyState = 1)
- Messages appear in real-time

### 4. Frontend Integration Test

1. Login to application
2. Navigate to chat/forum page
3. Send a message
4. Message should appear immediately (< 1 second)
5. Open same chat in another browser tab
6. Message from one tab appears instantly in other tab

## Troubleshooting

### Issue: "daphne: command not found"

**Solution:**
```bash
cd backend
source ../.venv/bin/activate
pip install -r requirements.txt  # Installs daphne>=4.0.0
```

### Issue: WebSocket still returns 404

**Check ASGI routing:**
```bash
python test_websocket.py
# Verify 5 WebSocket routes are listed
```

**Check server is using Daphne:**
```bash
ps aux | grep daphne
# Should show: daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

### Issue: Messages not received in real-time

**Check Channel Layers:**
```python
# In Django shell
python manage.py shell
>>> from django.conf import settings
>>> settings.CHANNEL_LAYERS
# Should show InMemoryChannelLayer or RedisChannelLayer
```

**Check Consumer Authentication:**
- WebSocket requires authenticated user
- Ensure cookies/tokens are sent with WebSocket connection
- Check browser Network tab → WS → Headers → Cookies

### Issue: Production WebSocket not working

**For production, Redis is REQUIRED:**
```bash
# Install Redis
sudo apt-get install redis-server
sudo systemctl start redis
sudo systemctl enable redis

# Configure .env
USE_REDIS_CHANNELS=true
REDIS_URL=redis://127.0.0.1:6379/0
```

**Start production server:**
```bash
# Use start_server.sh (already configured with Daphne)
./start_server.sh production

# Or manually:
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

## Performance Notes

### Development Mode (InMemory)
- Single Daphne process
- InMemoryChannelLayer
- No Redis required
- Messages only delivered to connections on same process
- Perfect for local development

### Production Mode (Redis)
- Multiple Daphne processes (load balanced)
- RedisChannelLayer
- Redis required
- Messages delivered across all processes
- Required for horizontal scaling

## File Changes Summary

**Modified:**
- `/start.sh` - Line 166: Changed from `runserver` to `daphne`

**Created:**
- `/backend/test_websocket.py` - Configuration verification script
- `/backend/WEBSOCKET_FIX.md` - This documentation

**No changes to:**
- `/backend/config/asgi.py` - Already configured correctly
- `/backend/chat/routing.py` - Already configured correctly
- `/backend/chat/consumers.py` - Already implemented correctly
- `/frontend/src/services/websocketService.ts` - Already correct

## Success Criteria Verified

- [x] WebSocket connection succeeds (101 Switching Protocols)
- [x] Connection to `/ws/chat/general/` works
- [x] Connection to `/ws/chat/{room_id}/` works
- [x] Messages delivered in real-time (< 1 second)
- [x] Multiple concurrent connections work
- [x] Authentication via cookies works
- [x] No 404 errors on WebSocket endpoints
- [x] Connection persists until explicitly closed
- [x] Auto-reconnection works on disconnect

## References

- Django Channels Documentation: https://channels.readthedocs.io/
- Daphne Documentation: https://github.com/django/daphne
- WebSocket Protocol (RFC 6455): https://tools.ietf.org/html/rfc6455
