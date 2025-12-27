# Production CD Pipeline - Complete Guide

## Overview

The `deploy-production.yml` workflow implements a comprehensive Continuous Deployment pipeline for production releases with:

- **Blue-Green Deployment**: Zero-downtime deployments with instant rollback capability
- **Semantic Versioning**: Structured version management (v1.0.0, v1.0.1, etc.)
- **Comprehensive Health Checks**: Database, Redis, API endpoints, frontend
- **Smoke Tests**: Critical workflow verification
- **Automatic Rollback**: Failure detection and automatic restoration
- **Release Notes Generation**: Automatic changelog from git commits
- **Multi-channel Notifications**: Telegram, GitHub status, email-ready
- **Pre-deployment Backups**: Database, media, and application state
- **Production Monitoring**: 5-minute stability check post-deployment

---

## Triggering Deployments

### Option 1: GitHub Release (Recommended for Production)

Create a release on GitHub:
```bash
gh release create v1.0.0 --title "Version 1.0.0" --notes "Release notes here"
```

This triggers the pipeline automatically with:
- Version: `v1.0.0` (from release tag)
- Release notes: Generated from git commit history
- Environment: production

### Option 2: Manual Workflow Dispatch

Trigger from GitHub Actions UI or CLI:
```bash
gh workflow run deploy-production.yml \
  -f version=v1.0.0 \
  -f reason="Critical hotfix for payment processing" \
  -f skip_tests=false
```

Parameters:
- `version`: Release version (e.g., v1.0.0)
- `reason`: Deployment reason (logged in notifications)
- `skip_tests`: Skip test suite (emergency only, not recommended)

### Option 3: Automatic on CI Success

When CI Pipeline Build completes successfully on `main` branch, production deployment is triggered automatically.

---

## Deployment Pipeline Phases

### Phase 1: Prepare Production Environment (5 min)

**Steps:**
1. Determine version (from release, input, or auto-generate)
2. Validate semantic versioning (v1.0.0, v1.0.1, etc.)
3. Generate deployment ID (prod-v1.0.0-20241227_183050)
4. Determine Docker image references (tagged with version)
5. Generate release notes from commit history
6. Create GitHub deployment record

**Outputs:**
- Version number
- Docker image references
- Deployment ID (for tracking)
- Release notes

---

### Phase 2: Pre-flight Checks (10 min)

**Steps:**
1. Verify release assets exist
2. Backup plan verification
3. Resource availability check

**Checks:**
- Deployment timeout configured (600s)
- Health check retries configured (30)
- Health check interval set (10s)

---

### Phase 3: Test Suite (30 min, can be skipped)

**Steps:**
1. Set up PostgreSQL 15 test database
2. Set up Redis test cache
3. Install Python dependencies
4. Run critical unit and integration tests
5. Upload test results

**Can be skipped:** Only in emergency situations via `skip_tests=true`

```bash
gh workflow run deploy-production.yml \
  -f version=v1.0.0 \
  -f reason="Emergency hotfix" \
  -f skip_tests=true
```

---

### Phase 4: Blue-Green Deployment (40 min)

**Steps:**

1. **Pre-deployment Backup** (5 min):
   - Database backup (JSON dump)
   - Media files backup (tar.gz)
   - Docker state snapshot
   - Current commit hash saved

   Location: `backups/pre-deploy-v1.0.0-20241227_183050/`

2. **Green Environment Setup** (30 min):
   - Authenticate with Docker registry (GHCR)
   - Pull new Docker images (backend + frontend)
   - Verify blue (current) environment status
   - Load production .env configuration
   - Create green docker-compose file
   - Start green environment (parallel to blue)
   - Run database migrations
   - Collect static files

3. **Blue-Green Principle**:
   ```
   BEFORE:
   ┌─────────────────┐
   │  BLUE (v1.0.0)  │ ← Production traffic
   └─────────────────┘

   DURING:
   ┌─────────────────┐
   │  BLUE (v1.0.0)  │ ← Production traffic
   └─────────────────┘
   ┌─────────────────┐
   │ GREEN (v1.0.1)  │ ← Testing & verification
   └─────────────────┘

   AFTER SUCCESS:
   ┌─────────────────┐
   │ GREEN (v1.0.1)  │ ← Production traffic (switched)
   └─────────────────┘
   ```

**Advantages:**
- Zero-downtime deployments
- Instant rollback if issues detected
- Full environment testing before traffic switch
- Blue acts as fallback

---

### Phase 5: Health Checks (20 min)

**Checks Performed:**

1. **Backend Health**:
   ```bash
   GET https://the-bot.ru/api/health/
   ```
   - Retries: 30 attempts with 10s interval
   - Timeout: 5 minutes total
   - Success criteria: HTTP 200

2. **Frontend Health**:
   ```bash
   GET https://the-bot.ru/
   ```
   - Retries: 10 attempts with 5s interval
   - Success criteria: HTTP 200

3. **Database Connectivity**:
   ```bash
   docker-compose exec -T backend python manage.py dbshell
   SELECT 1;
   ```
   - Verifies database connection
   - Tests SQL execution

4. **Redis Connectivity**:
   ```bash
   docker-compose exec -T redis redis-cli ping
   ```
   - Expected response: PONG
   - Verifies caching layer

**Failure Handling:**
- If health checks fail, pipeline stops
- Rollback is automatically triggered
- Notifications sent to ops team

---

### Phase 6: Smoke Tests (10 min)

**Critical Endpoint Tests:**
- `/api/health/` - System health
- `/api/system/readiness/` - Readiness probe
- `/api/v1/auth/status/` - Authentication
- `/admin/` - Admin panel
- `/` - Frontend

**Database Operation Tests:**
- Basic API operations
- User authentication flow
- Cache operations

**Smoke Test Criteria:**
- All endpoints respond
- HTTP 200 (or expected error)
- No internal server errors (500+)
- Database queries execute

---

### Phase 7: Traffic Switch (15 min)

**Only executed if ALL health checks and smoke tests pass**

**Steps:**
1. Stop blue (old) environment
2. Rename green docker-compose to main
3. Verify green is now active

**Result:**
- Production traffic now served by green
- Blue environment stopped (can be restarted for rollback)
- No downtime experienced by users

---

### Phase 8: Post-Deployment Verification (15 min)

**Steps:**

1. **Stability Monitoring** (5 minutes):
   - Continuous health checks
   - Error rate monitoring
   - Max 3 errors allowed before rollback trigger

2. **Metrics Collection**:
   - API response time
   - HTTP status codes
   - Database query performance

**Failure Handling:**
- If >3 errors in 5 minutes, rollback triggered
- Automatic notifications to ops team

---

### Phase 9: Notifications (2 min)

**Telegram Notification** (production alerts):
```
✅ Production Deployment Successful

🔖 Version: v1.0.1
📋 Deployment ID: prod-v1.0.1-20241227_183050
📝 Commit: abc1234
👤 Deployed by: devops-user
⏰ Time: 2024-12-27 18:30:50 UTC
```

**GitHub Deployment Status**:
- Deployment marked as "success" or "failure"
- Status visible in GitHub UI
- Links to production environment

---

### Phase 10: Automatic Rollback (On Failure)

**Triggered automatically if:**
- Health checks fail
- Smoke tests fail
- Post-deployment stability check fails

**Rollback Steps:**
1. Stop green environment
2. Restore blue environment from previous state
3. Verify blue is serving traffic
4. Send rollback notification

**Rollback Notification**:
```
🔄 AUTOMATIC ROLLBACK EXECUTED
Version: v1.0.1
Deployment ID: prod-v1.0.1-20241227_183050
Time: 2024-12-27 18:31:30 UTC
```

---

## Secret Configuration

Required GitHub secrets (production environment):

```bash
PRODUCTION_HOST          # Server hostname/IP
PRODUCTION_USER          # SSH user
PRODUCTION_PATH          # Deployment directory
PRODUCTION_SSH_KEY       # SSH private key (PEM format)
TELEGRAM_BOT_TOKEN       # Telegram bot token
TELEGRAM_PUBLIC_CHAT_ID  # Telegram notifications channel
TELEGRAM_LOG_CHAT_ID     # Telegram error/rollback channel
GITHUB_TOKEN             # Auto-provided by GitHub Actions
```

### Setup Secrets

```bash
# Via GitHub CLI
gh secret set PRODUCTION_HOST --body "the-bot.ru"
gh secret set PRODUCTION_USER --body "deploy"
gh secret set PRODUCTION_PATH --body "/opt/the-bot"
gh secret set PRODUCTION_SSH_KEY < ~/.ssh/id_rsa
gh secret set TELEGRAM_BOT_TOKEN --body "123456:ABC..."
gh secret set TELEGRAM_PUBLIC_CHAT_ID --body "-1001234567890"
gh secret set TELEGRAM_LOG_CHAT_ID --body "-1001234567890"
```

---

## Environment Files

### .env.production

Required on production server (`${PRODUCTION_PATH}/.env.production`):

```bash
# Core
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=<50+ char secure key>
ALLOWED_HOSTS=the-bot.ru,www.the-bot.ru

# Database
DATABASE_URL=postgresql://user:pass@db-host:5432/thebot_prod

# Redis
REDIS_URL=redis://redis-host:6379/1

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=<your-email>
EMAIL_HOST_PASSWORD=<your-password>

# External Services
YOOKASSA_SHOP_ID=<shop-id>
YOOKASSA_SECRET_KEY=<secret>
OPENROUTER_API_KEY=<key>
TELEGRAM_BOT_TOKEN=<token>
SUPABASE_URL=<url>
SUPABASE_KEY=<key>

# Frontend
FRONTEND_URL=https://the-bot.ru
```

---

## Common Scenarios

### Scenario 1: Normal Release Deployment

```bash
# Create release on GitHub
gh release create v1.0.1 \
  --title "Version 1.0.1" \
  --notes "Bug fixes and improvements"
```

**Flow:**
1. Tests run automatically ✓
2. Blue-green deployment ✓
3. Health checks pass ✓
4. Traffic switches to green ✓
5. Post-deployment monitoring ✓
6. Success notification sent ✓

---

### Scenario 2: Critical Hotfix (Skip Tests)

```bash
# Emergency deployment
gh workflow run deploy-production.yml \
  -f version=v1.0.1-hotfix \
  -f reason="Critical payment processing bug" \
  -f skip_tests=true
```

**Flow:**
1. Skip tests ⚠️
2. Blue-green deployment ✓
3. Health checks (stricter validation) ✓
4. Manual review recommended
5. Traffic switches ✓

**⚠️ WARNING:** Use only in true emergencies!

---

### Scenario 3: Automatic Rollback (Test Failure)

```
Pipeline execution:
1. Tests fail ✗
2. Deployment aborted
3. NO changes to production
4. Notification sent to ops
```

---

### Scenario 4: Deployment Failure Recovery

If deployment fails after health checks:

```bash
# 1. Automatic rollback triggers
#    - Blue environment restored
#    - Traffic reverted
#    - Notifications sent

# 2. Investigate failure
#    - Check deployment logs in GitHub Actions
#    - Review health check results
#    - Examine application logs

# 3. Fix and retry
gh release create v1.0.2 \
  --title "Version 1.0.2 - Fixes from v1.0.1 failure" \
  --notes "Addressed: [issue description]"
```

---

## Monitoring & Troubleshooting

### View Deployment Logs

**GitHub Actions UI:**
```
Repository → Actions → CD Production Pipeline → Latest run
```

**Sections:**
- Prepare: Version determination, image references
- Health Checks: Each check result
- Smoke Tests: Endpoint test results
- Traffic Switch: Blue-green cutover details
- Post-Deployment: Stability metrics

### Common Issues

#### Issue: Health checks fail

**Symptoms:**
- Backend health check timeout after 30 attempts
- Error: "Backend health check failed"

**Diagnosis:**
```bash
# SSH to production server
ssh deploy@the-bot.ru
cd /opt/the-bot

# Check docker status
docker-compose -f docker-compose.green.yml ps

# Check backend logs
docker-compose -f docker-compose.green.yml logs backend

# Check database
docker-compose -f docker-compose.green.yml exec -T backend \
  python manage.py dbshell
SELECT 1;
```

**Solutions:**
1. Increase health check timeout (change `HEALTH_CHECK_INTERVAL`)
2. Check database connectivity
3. Verify environment variables in .env.production
4. Check disk space and memory

#### Issue: Database migration failure

**Symptoms:**
- WARNING in logs: "Migrations on green environment had issues"
- Health checks fail

**Diagnosis:**
```bash
# Check migration status
docker-compose -f docker-compose.green.yml exec -T backend \
  python manage.py showmigrations

# Run migrations manually
docker-compose -f docker-compose.green.yml exec -T backend \
  python manage.py migrate --verbosity=2
```

**Solutions:**
1. Rollback and fix migration issues
2. Test migrations in staging first
3. Update backup strategy

#### Issue: Automatic rollback triggered

**Symptoms:**
- "AUTOMATIC ROLLBACK EXECUTED" notification
- Production reverted to blue environment

**Next Steps:**
1. Investigate rollback logs in GitHub Actions
2. Check why health checks failed
3. Fix issues in code
4. Test in staging
5. Redeploy with new version

---

## Version Management

### Semantic Versioning Format

```
v1.0.0-rc1
 │ │ │ │
 │ │ │ └─ Pre-release: rc1, beta, alpha (optional)
 │ │ └─── Patch version (bug fixes)
 │ └───── Minor version (new features, backward compatible)
 └─────── Major version (breaking changes)
```

**Examples:**
- `v1.0.0` - Initial release
- `v1.0.1` - Patch: bug fix
- `v1.1.0` - Minor: new feature
- `v2.0.0` - Major: breaking changes
- `v1.0.0-rc1` - Release candidate

### Auto-Generated Versions

If no version specified, auto-generated from timestamp:
```
v2024.12.27-183050
  │    │  │  │
  │    │  │  └─ Time (HHMMSS)
  │    │  └──── Day (DD)
  │    └─────── Month (MM)
  └──────────── Year (YYYY)
```

---

## Best Practices

### 1. Always Test in Staging First
```bash
# Test changes in staging before production
# Reference: deploy-staging.yml
```

### 2. Use Meaningful Release Notes
```bash
gh release create v1.0.1 \
  --title "Version 1.0.1" \
  --notes "- Fixed: Chat message delivery
- Improved: API response time
- Updated: Dependencies (5 packages)
- Security: Fixed XSS vulnerability"
```

### 3. Monitor Post-Deployment
- Check application logs for 10 minutes
- Monitor error rates
- Verify database performance
- Check user feedback

### 4. Document Rollback Reason
If automatic rollback occurs:
1. Document in incident log
2. Create ticket to fix issue
3. Post-mortem review
4. Update test cases

### 5. Version Hotfixes Clearly
```bash
# For emergency fixes
gh release create v1.0.1-hotfix-1 \
  --title "Hotfix: Payment processing" \
  --notes "Emergency fix for issue #123"
```

---

## Rollback Procedures

### Automatic Rollback (Automatic)

Triggered automatically if:
- Health checks fail
- Smoke tests fail
- Post-deployment errors detected

**Process:**
1. Stop green environment
2. Restore blue environment
3. Traffic reverted
4. Notifications sent

### Manual Rollback

```bash
# SSH to production
ssh deploy@the-bot.ru
cd /opt/the-bot

# List recent versions
docker images | grep backend

# Restore specific version
# Example: restore v1.0.0 (blue)
git checkout main
git pull origin main
docker-compose down
docker-compose up -d
```

---

## Integration Points

### GitHub Deployments

Each deployment creates a GitHub deployment record:
- Environment: production
- Status: success/failure
- URL: https://the-bot.ru
- Description: Version, deployment ID, commit

### GitHub Status Checks

Deployment marked as check in PR (if triggered from PR):
- ✅ Success: Deployment passed all checks
- ❌ Failure: Tests failed, deployment skipped
- ⏳ Pending: Deployment in progress

---

## Performance Metrics

### Expected Deployment Duration

| Phase | Duration | Critical |
|-------|----------|----------|
| Prepare | 5 min | No |
| Pre-flight | 10 min | No |
| Tests | 30 min | Yes* |
| Blue-Green Deploy | 40 min | Yes |
| Health Checks | 20 min | Yes |
| Smoke Tests | 10 min | Yes |
| Traffic Switch | 5 min | Yes |
| Post-Deploy Verify | 15 min | Yes |
| **Total** | **~135 min** | |

*Can be skipped in emergencies

### Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| Deployment time | <2.5 hours | ~2 hours |
| Rollback time | <10 minutes | ~5 minutes |
| API response time | <100ms | 50-80ms |
| Database query time | <50ms | 20-40ms |
| Health check timeout | 5 minutes | 5 minutes |

---

## Support & Escalation

### Deployment Issues

1. **Check deployment logs** in GitHub Actions
2. **Verify secrets** are configured
3. **Test in staging** with same changes
4. **Manual rollback** if needed
5. **Post-mortem** after resolution

### Contact

- DevOps Lead: [contact info]
- On-call: [escalation process]
- Slack: #devops-alerts

---

## Changelog

### v1.0.0 (Initial Release)

Features:
- Blue-green deployment
- Semantic versioning
- Comprehensive health checks
- Automatic rollback
- Release notes generation
- Multi-channel notifications
- Pre-deployment backups
- Post-deployment monitoring

---

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [Semantic Versioning](https://semver.org/)
- [Blue-Green Deployment](https://en.wikipedia.org/wiki/Blue%E2%80%93green_deployment)
- [Project README](../../README.md)

