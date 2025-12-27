# WebSocket Troubleshooting Guide

**Quick Reference for Real-Time Communication Issues**

---

## Quick Status Check

### WebSocket Health

\`\`\`bash
# Check if WebSocket gateway is running
curl http://localhost:8001/health/

# Check Redis (WebSocket backend)
redis-cli ping

# Check Channels worker
docker logs thebot-channels-worker | tail -20
\`\`\`

---

## Common Issues

### Connection Fails to Establish

**Symptoms**: "WebSocket connection failed", stuck on "Connecting..."

**Quick Fix**:
\`\`\`bash
# Check if WebSocket service running
curl http://localhost:8001/health/

# Restart if needed
docker restart thebot-websocket

# Check firewall (port 8001 or 443 for WSS)
netstat -tuln | grep 8001
\`\`\`

**Include auth token**:
\`\`\`javascript
const token = localStorage.getItem('token');
const ws = new WebSocket(\`ws://\${host}/ws/chat/?token=\${token}\`);
\`\`\`

### Connection Drops After 30 Seconds

**Symptoms**: Connection stable, then disconnects

**Cause**: Inactivity timeout

**Fix**:
\`\`\`javascript
// Send keepalive
setInterval(() => {
    ws.send(JSON.stringify({ type: 'ping' }));
}, 30000);  // Every 30 seconds

// Reconnect on close
ws.onclose = () => {
    setTimeout(() => {
        ws = new WebSocket(...);
    }, 1000);
};
\`\`\`

### Messages Not Being Delivered

**Symptoms**: Message sent but not received

**Check**:
\`\`\`bash
# Check message in database
psql $DATABASE_URL -c "SELECT * FROM chat_message WHERE id = [id] ORDER BY created_at DESC LIMIT 5;"

# Check Redis
redis-cli LLEN "django_channels:messages"

# Check if recipient connected
docker logs thebot-channels-worker | grep "connect"
\`\`\`

### Slow Message Delivery

**Symptoms**: Message takes 5+ seconds to deliver

**Check**:
\`\`\`bash
# Check Redis latency
redis-cli --latency

# Check worker load
docker stats thebot-channels-worker

# Check WebSocket gateway memory
docker stats thebot-websocket
\`\`\`

**Fix**: Scale workers
\`\`\`bash
docker run --replicas 5 thebot-channels-worker
\`\`\`

---

## Monitoring

### Essential Metrics

\`\`\`bash
# Active connections
redis-cli HGETALL "django_channels:group:*" | wc -l

# Message queue depth
redis-cli LLEN "django_channels:messages"

# Redis memory
redis-cli INFO memory | grep "used_memory_human"
\`\`\`

---

## Emergency Recovery

**All Connections Dropped**:
\`\`\`bash
# Restart Redis
docker restart redis

# Restart Channels worker
docker restart thebot-channels-worker

# Restart WebSocket gateway
docker restart thebot-websocket
\`\`\`

**Memory Exhausted**:
\`\`\`bash
# Restart gateway (loses connections, clients reconnect)
docker restart thebot-websocket

# Check for memory leak
docker stats thebot-websocket --no-stream
\`\`\`

---

## Testing WebSocket

\`\`\`bash
# Manual test using wscat (npm install -g wscat)
wscat -c ws://localhost:8001/ws/chat/?token=your_token

# Send: {"type": "chat_message", "content": "Hello"}
# Should receive similar message back
\`\`\`

---

## Related Guides

- [INCIDENT_RESPONSE.md](../INCIDENT_RESPONSE.md)
- [API Troubleshooting](api.md)
- [Database Troubleshooting](database.md)
