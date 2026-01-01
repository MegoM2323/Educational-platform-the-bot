# Database Troubleshooting Guide

**Quick Reference for PostgreSQL Issues**

---

## Quick Diagnostics

### Is the Database Running?

\`\`\`bash
pg_isready -h $POSTGRES_HOST -p 5432

# Output:
# accepting connections      → DB is running
# rejecting connections       → DB is running but not accepting
# no attempt was made         → DB is not running
\`\`\`

### Current Status

\`\`\`bash
# Check all connections
psql $DATABASE_URL -c "SELECT count(*) as total_connections FROM pg_stat_activity;"

# Check slow queries (> 1 sec)
psql $DATABASE_URL -c "SELECT query, mean_exec_time FROM pg_stat_statements WHERE mean_exec_time > 1000 ORDER BY mean_exec_time DESC LIMIT 10;"

# Check table sizes
psql $DATABASE_URL -c "SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) FROM pg_tables ORDER BY pg_total_relation_size DESC LIMIT 20;"
\`\`\`

---

## Common Issues

### Connection Pool Exhausted

**Symptoms**: All connections in use, new requests queue

**Quick Fix**:
\`\`\`bash
# Restart connection pool
python manage.py shell -c "from django.db import connection; connection.close()"

# Or restart API container
docker restart thebot-backend
\`\`\`

### Slow Queries

**Symptoms**: Response time > 5 seconds

**Quick Fix**:
\`\`\`bash
# Identify slow query
psql $DATABASE_URL -c "EXPLAIN ANALYZE [slow_query]"

# Add index if missing
CREATE INDEX idx_name ON table(column);
\`\`\`

### Disk Space Full

**Symptoms**: "No space left on device"

**Quick Fix**:
\`\`\`bash
# Check disk usage
df -h

# Check database size
psql $DATABASE_URL -c "SELECT datname, pg_size_pretty(pg_database_size(datname)) FROM pg_database;"

# Delete old data or expand disk
DELETE FROM messages WHERE created_at < NOW() - INTERVAL '1 year';
VACUUM FULL messages;
\`\`\`

### Replication Lag

**Symptoms**: Replica showing stale data

**Check**:
\`\`\`bash
# Check lag
psql $DATABASE_URL -c "SELECT EXTRACT(EPOCH FROM (NOW() - pg_last_xact_replay_time()))::INT as lag_seconds;"

# Fix: Check replica connection and restart if needed
docker restart thebot-postgres-replica
\`\`\`

---

## Detailed Guides

See related documentation:
- [INCIDENT_RESPONSE.md](../INCIDENT_RESPONSE.md) - Incident procedures
- [API Troubleshooting](api.md) - API-related issues
- [WebSocket Troubleshooting](websocket.md) - Real-time communication

---

## Emergency Recovery

**Database Won't Start**:
\`\`\`bash
tail -100 /var/log/postgresql/postgresql.log
docker restart thebot-postgres
\`\`\`

**Data Corruption**:
- Restore from backup (see DEPLOYMENT.md)

**Complete Failure**:
- Follow disaster recovery procedures

