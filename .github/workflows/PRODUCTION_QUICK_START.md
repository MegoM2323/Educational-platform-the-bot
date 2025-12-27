# Production Deployment - Quick Start

## TL;DR - Deploy to Production

### Method 1: GitHub Release (Recommended)

```bash
# Create and push a release
gh release create v1.0.1 \
  --title "Version 1.0.1" \
  --notes "Bug fixes and improvements"

# Pipeline triggers automatically
# Monitor: GitHub Actions → CD Production Pipeline
```

### Method 2: Manual Dispatch

```bash
# Via CLI
gh workflow run deploy-production.yml \
  -f version=v1.0.1 \
  -f reason="Feature release" \
  -f skip_tests=false

# Or via GitHub Actions UI:
# Actions → CD Production Pipeline → Run workflow
```

---

## Deployment Checklist

Before deploying:

- [ ] Tests pass in staging
- [ ] All features tested in staging
- [ ] Release notes prepared
- [ ] Backup strategy verified
- [ ] Team notified
- [ ] Runbook ready (this document)

---

## What Gets Deployed

```
Backend:  ghcr.io/repo/backend:v1.0.1
Frontend: ghcr.io/repo/frontend:v1.0.1
```

Tagged and deployed with zero downtime.

---

## Deployment Pipeline

```
1. Prepare (5 min)
   └─ Version determination, image references

2. Pre-flight (10 min)
   └─ Backup plan, resource checks

3. Tests (30 min, optional)
   └─ Unit + integration tests

4. Blue-Green Deploy (40 min)
   └─ Green env setup, migrations, static files

5. Health Checks (20 min)
   └─ Backend, frontend, database, Redis

6. Smoke Tests (10 min)
   └─ Critical endpoints, API operations

7. Traffic Switch (5 min)
   └─ Blue → Green cutover

8. Post-Deploy Verify (15 min)
   └─ Stability check, metrics

9. Notifications (2 min)
   └─ Telegram, GitHub status

10. Rollback (auto, on failure)
    └─ Restore blue environment
```

**Total time: ~135 minutes**

---

## Monitoring Deployment

### GitHub Actions UI

```
Repository → Actions → CD Production Pipeline → Latest run
```

**Status indicators:**
- 🟡 In progress
- ✅ Success
- ❌ Failed
- 🔄 Rolled back

### Key Milestones

1. "Deploy green environment" - Actual deployment started
2. "Health Checks" - App ready for traffic
3. "Switch traffic to green" - Live!
4. "Post-Deployment Verification" - Final stability check

---

## Deployment Success

When you see:

```
✅ Production Deployment Successful

🔖 Version: v1.0.1
📋 Deployment ID: prod-v1.0.1-20241227_183050
📝 Commit: abc1234
👤 Deployed by: you
⏰ Time: 2024-12-27 18:30:50 UTC
```

✓ Production updated
✓ No downtime
✓ Zero-loss cutover
✓ Rollback ready if needed

---

## Emergency Deployment

⚠️ **Only use for critical issues**

```bash
gh workflow run deploy-production.yml \
  -f version=v1.0.1-emergency \
  -f reason="Critical bug fix" \
  -f skip_tests=true
```

**What gets skipped:**
- ❌ Test suite (30 min saved)
- ✅ Health checks (still run, stricter)
- ✅ Smoke tests (still run)

**Time saved:** 30 minutes
**Risk:** Higher (no tests run)

---

## If Deployment Fails

### Automatic Rollback

The pipeline will automatically rollback if:
- Tests fail
- Health checks fail
- Smoke tests fail
- Stability check fails

You'll receive:

```
🔄 AUTOMATIC ROLLBACK EXECUTED
Version: v1.0.1
Deployment ID: prod-v1.0.1-20241227_183050
Time: 2024-12-27 18:31:30 UTC
```

### Recovery Steps

1. **Check logs** in GitHub Actions
2. **Fix the issue** (code or config)
3. **Test in staging** with same changes
4. **Redeploy** with new version:

```bash
gh release create v1.0.2 \
  --title "Version 1.0.2" \
  --notes "Fixed issue from v1.0.1"
```

---

## Rollback (Manual)

If you need to rollback manually:

```bash
# SSH to production
ssh deploy@the-bot.ru
cd /opt/the-bot

# Check running version
docker-compose ps

# Check available versions
docker images | grep backend

# Restore previous version
# Pipeline stores blue environment during deployment

# Start blue environment
docker-compose down
git checkout HEAD~1  # Go back one commit
docker-compose up -d

# Verify
curl https://the-bot.ru/api/health/
```

---

## Secrets Setup

One-time setup for first deployment:

```bash
# In GitHub repository

gh secret set PRODUCTION_HOST \
  --body "the-bot.ru"

gh secret set PRODUCTION_USER \
  --body "deploy"

gh secret set PRODUCTION_PATH \
  --body "/opt/the-bot"

gh secret set PRODUCTION_SSH_KEY \
  < ~/.ssh/id_rsa

gh secret set TELEGRAM_BOT_TOKEN \
  --body "123456:ABC..."

gh secret set TELEGRAM_PUBLIC_CHAT_ID \
  --body "-1001234567890"

gh secret set TELEGRAM_LOG_CHAT_ID \
  --body "-1001234567890"
```

**Or via GitHub UI:**
```
Settings → Secrets and variables → Actions → New repository secret
```

---

## Production Server Setup

Required files on production server:

```
/opt/the-bot/
├── .env.production          ← Configuration
├── docker-compose.yml       ← Current (blue/green)
├── docker-compose.green.yml ← New (during deploy)
├── backups/
│   └── pre-deploy-v1.0.1.../
│       ├── db_backup.json
│       ├── media_backup.tar.gz
│       └── docker_state.txt
└── ... (application files)
```

---

## Environment Variables

Minimal `.env.production`:

```bash
# Core
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=<50+ chars>
ALLOWED_HOSTS=the-bot.ru

# Database
DATABASE_URL=postgresql://user:pass@db:5432/thebot_prod

# Redis
REDIS_URL=redis://redis:6379/1

# Services
YOOKASSA_SHOP_ID=<id>
YOOKASSA_SECRET_KEY=<key>
TELEGRAM_BOT_TOKEN=<token>

# Other
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=<email>
EMAIL_HOST_PASSWORD=<pass>
```

---

## Verification Endpoints

After deployment, verify endpoints:

```bash
# Health check
curl https://the-bot.ru/api/health/

# Readiness
curl https://the-bot.ru/api/system/readiness/

# Frontend
curl https://the-bot.ru/

# Admin panel
curl https://the-bot.ru/admin/
```

Expected responses:
- HTTP 200 (success)
- JSON body with status info
- No errors in logs

---

## Monitoring Post-Deploy

For 10 minutes after deployment:

1. **Check logs**:
```bash
docker-compose logs backend | tail -100
docker-compose logs frontend | tail -100
```

2. **Monitor metrics**:
```bash
# API response time
curl -w "Response time: %{time_total}s\n" https://the-bot.ru/api/health/

# Database performance
docker-compose exec -T backend python manage.py dbshell
EXPLAIN ANALYZE SELECT * FROM accounts_user LIMIT 10;
```

3. **Check error rates**:
```bash
# Look for 500 errors in logs
docker-compose logs backend | grep ERROR
docker-compose logs frontend | grep ERROR
```

---

## Version Naming

Use semantic versioning:

```
v1.0.0    - Initial release
v1.0.1    - Bug fix
v1.1.0    - New feature (backward compatible)
v2.0.0    - Breaking changes
v1.0.0-rc1 - Release candidate
```

**Auto-generated if not specified:**
```
v2024.12.27-183050 (timestamp-based)
```

---

## Support

### During Deployment

Deployment in progress? Check:
1. GitHub Actions logs (real-time)
2. Production server logs (via SSH)
3. Slack #devops-alerts channel

### After Deployment

Issues found? Consider:
1. Wait 5 minutes (system stabilizing)
2. Check application logs
3. Verify database connectivity
4. Manual rollback if critical
5. Post-mortem review

### Escalation

Contact:
- DevOps: [email]
- On-call: [phone]
- Slack: @devops-team

---

## Common Scenarios

### Scenario: New feature release

```bash
# Test in staging first
# See: deploy-staging.yml

# Create production release
gh release create v1.1.0 \
  --title "Version 1.1.0 - New Dashboard" \
  --notes "- Added analytics dashboard
- Improved performance by 30%
- Fixed payment flow bug"

# Monitor deployment
# Check: GitHub Actions → CD Production Pipeline
```

### Scenario: Emergency hotfix

```bash
# For critical bug fix (skip tests)
gh workflow run deploy-production.yml \
  -f version=v1.0.1-hotfix \
  -f reason="Critical payment bug" \
  -f skip_tests=true

# Monitor closely (health checks still run)
```

### Scenario: Rollback incident

```bash
# Automatic rollback triggered
# You'll see notification

# Steps:
1. Investigate what went wrong
2. Fix the issue
3. Wait for stability
4. Create new release with fix
5. Redeploy

gh release create v1.0.2 \
  --title "Version 1.0.2" \
  --notes "Fixed issue in v1.0.1"
```

---

## FAQ

**Q: How long does deployment take?**
A: ~2 hours normally, ~1.5 hours with tests skipped

**Q: Can I cancel deployment?**
A: Yes, in GitHub Actions UI (before traffic switch)

**Q: What if database migration fails?**
A: Automatic rollback triggers, blue restored

**Q: Can I see what changed?**
A: Yes, git commit log shows changes

**Q: How far back can I rollback?**
A: To any previous version (with blue-green strategy)

**Q: Is downtime possible?**
A: No, blue-green strategy ensures zero downtime

**Q: Can tests be skipped?**
A: Only in emergencies (via skip_tests=true)

**Q: Who can deploy?**
A: Anyone with repository push access (configurable)

---

## Quick Commands Reference

```bash
# View all deployments
gh api repos/{owner}/{repo}/deployments

# Get deployment status
gh api repos/{owner}/{repo}/deployments/{deployment_id}/statuses

# View workflow runs
gh run list --workflow=deploy-production.yml

# View latest deployment
gh run view --log -w deploy-production.yml

# Trigger deployment
gh workflow run deploy-production.yml \
  -f version=v1.0.1 \
  -f reason="Release" \
  -f skip_tests=false

# Create release (alternative)
git tag v1.0.1
git push origin v1.0.1
# Or use GitHub UI
```

---

## Next Steps

1. **Configure secrets** (one-time setup)
2. **Set up production server** (.env.production, docker-compose)
3. **Test in staging** (deploy-staging.yml)
4. **Deploy to production** (this pipeline)
5. **Monitor continuously** (application logs, metrics)

---

**For detailed documentation, see: `PRODUCTION_DEPLOYMENT_GUIDE.md`**

