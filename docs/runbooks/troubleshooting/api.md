# API Troubleshooting Guide

**Quick Reference for REST API Issues**

---

## Quick Status Check

### API Health

\`\`\`bash
# Check if API is responding
curl -i http://localhost:8000/api/health/

# Check detailed status
curl http://localhost:8000/api/system/health/
curl http://localhost:8000/api/system/readiness/
\`\`\`

---

## Common Issues

### 500 Internal Server Error

**Symptoms**: HTTP 500 error, request fails

**Diagnosis**:
\`\`\`bash
# Check API logs
docker logs thebot-backend | tail -50

# Check if recent deployment caused it
git log --oneline -5

# Test database connection
psql $DATABASE_URL -c "SELECT 1"
\`\`\`

**Quick Fixes**:
\`\`\`bash
# Rollback if recent deployment
git revert -m 1 [commit_hash]
docker build -t thebot/backend:latest .
docker restart thebot-backend

# Or just restart API
docker restart thebot-backend
\`\`\`

### Timeout (408 / 504)

**Symptoms**: Request takes too long, error after 30+ seconds

**Causes**:
- Database slow queries
- External service timeout
- High load on API

**Quick Fix**:
\`\`\`bash
# Check database performance
psql $DATABASE_URL -c "SELECT query, mean_exec_time FROM pg_stat_statements WHERE mean_exec_time > 1000 ORDER BY mean_exec_time DESC LIMIT 5;"

# Check API response times
curl http://localhost:8000/api/system/metrics/ | jq '.response_time_p95'

# Scale up if needed
kubectl scale deployment/backend --replicas=5
\`\`\`

### 401 Unauthorized / 403 Forbidden

**Symptoms**: Authentication/authorization failed

**Quick Fix**:
\`\`\`bash
# Include Authorization header
curl -H "Authorization: Token $TOKEN" https://api.thebot.app/api/users/me/

# Check token validity
curl -X POST https://api.thebot.app/api/auth/token/validate/ \
  -H "Authorization: Token $TOKEN"
\`\`\`

### 404 Not Found

**Symptoms**: Endpoint not found

**Check**:
\`\`\`bash
# Verify endpoint exists
curl https://api.thebot.app/api/users/

# Check resource ID is correct
curl https://api.thebot.app/api/users/123/
\`\`\`

### 429 Rate Limit

**Symptoms**: Too many requests

**Quick Fix**:
\`\`\`bash
# Wait and retry
# Check rate limit headers
curl -i https://api.thebot.app/api/users/me/ | grep "X-RateLimit"

# Batch requests if possible
POST /api/assignments/bulk/ -d '{"ids": [1, 2, 3, ...]}'
\`\`\`

---

## Monitoring

### Essential Metrics

\`\`\`bash
# Error rates
curl http://localhost:8000/api/system/metrics/ | jq '.request_errors'

# Response times
curl http://localhost:8000/api/system/metrics/ | jq '.response_time_p95'

# Request volume
curl http://localhost:8000/api/system/metrics/ | jq '.requests_per_second'
\`\`\`

---

## Emergency Recovery

**API Completely Down**:
\`\`\`bash
docker restart thebot-backend
curl http://localhost:8000/api/health/

# If restart fails, check logs
docker logs thebot-backend | tail -100
\`\`\`

---

## Related Guides

- [INCIDENT_RESPONSE.md](../INCIDENT_RESPONSE.md)
- [Database Troubleshooting](database.md)
- [WebSocket Troubleshooting](websocket.md)
- [API_GUIDE.md](../../API_GUIDE.md)
