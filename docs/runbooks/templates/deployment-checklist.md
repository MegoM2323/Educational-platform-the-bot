# Pre-Deployment Checklist Template

Use this checklist before every production deployment to ensure safety and consistency.

---

## Deployment Information

| Item | Value |
|------|-------|
| **Version** | v_____ |
| **Release Date** | __________ |
| **Deployment Strategy** | [ ] Blue-Green [ ] Canary [ ] Rolling [ ] Hotfix |
| **Changes Included** | __________ |
| **Database Migrations** | [ ] Yes [ ] No |
| **New Dependencies** | [ ] Yes [ ] No |
| **Configuration Changes** | [ ] Yes [ ] No |
| **Third-party API Changes** | [ ] Yes [ ] No |

---

## Pre-Deployment Phase (30 minutes before)

### Team Readiness

- [ ] DevOps engineer assigned and available
- [ ] Tech lead assigned and available
- [ ] QA engineer assigned and available
- [ ] Database admin available (if migrations)
- [ ] Incident commander identified
- [ ] Support team notified
- [ ] Stakeholders informed

### Communication Plan

- [ ] Status page updated with scheduled maintenance window
- [ ] Team Slack channel created/updated
- [ ] Deployment timeline shared: Start ______ End _______
- [ ] Rollback contact list confirmed
- [ ] Support escalation path established

### Code Quality Verification

- [ ] All tests passing (run test suite)
  ```
  npm test
  pytest
  ```
- [ ] Code review completed
- [ ] Security scan passed
  ```
  ./scripts/security-scan.sh
  ```
- [ ] No critical CVEs in dependencies
  ```
  npm audit
  pip-audit
  ```
- [ ] Linting passed
  ```
  npm run lint
  black backend/ --check
  ```
- [ ] Type checking passed (TypeScript, mypy)
  ```
  tsc --noEmit
  mypy backend/
  ```

### Environment Verification

- [ ] `.env.production` file exists
- [ ] All required variables set:
  - [ ] SECRET_KEY (min 50 characters)
  - [ ] DATABASE_URL (connection string)
  - [ ] REDIS_URL (Redis connection)
  - [ ] ALLOWED_HOSTS (domain list)
  - [ ] YOOKASSA_SHOP_ID & YOOKASSA_SECRET_KEY
  - [ ] API keys (all third-party services)
- [ ] No sensitive data in git history
- [ ] Configuration matches deployment guide

### Database Safety

- [ ] Database backup created
  ```
  docker-compose -f docker-compose.prod.yml exec postgres pg_dump \
    -U postgres -F c -f /backups/pre_deploy_$(date +%Y%m%d_%H%M%S).dump thebot_db
  ```
- [ ] Backup verified (can read contents)
- [ ] Backup size reasonable: ____________ MB
- [ ] Backup copied to external storage (S3, etc.)
- [ ] Database replication health checked
- [ ] Slow query log enabled
- [ ] Database connections available: ______ of 200

### Migration Safety

If database migrations included:

- [ ] Migrations tested on staging environment
- [ ] Rollback procedure documented
- [ ] Migration time estimated: ______ seconds
- [ ] Zero-downtime migration confirmed (no locks)
- [ ] Schema backward compatible
- [ ] Data migration script has rollback
- [ ] No DDL on large tables (verify size: ______ rows)

### Deployment Infrastructure

- [ ] Docker images built successfully
  ```
  docker-compose build --no-cache
  ```
- [ ] Image size reasonable: ______ MB
- [ ] Image scan shows no critical vulnerabilities
- [ ] Docker registry accessible
- [ ] Kubernetes manifests updated (if applicable)
- [ ] Load balancer configured correctly
- [ ] SSL certificates valid and not expiring soon (expires: _______)
- [ ] Rate limiting configured
- [ ] Cache warmed/cleared appropriately

### Monitoring Setup

- [ ] Prometheus targets verified
- [ ] Alert rules configured and tested
- [ ] Grafana dashboards opened in separate tab
- [ ] Log aggregation system online
- [ ] Error tracking system online (Sentry, etc.)
- [ ] Baseline metrics captured:
  - [ ] Average response time: ______ ms
  - [ ] Error rate: ______ %
  - [ ] Cache hit rate: ______ %
  - [ ] Database query time: ______ ms

### Health Check Script Prepared

- [ ] `verify-deployment.sh` reviewed
- [ ] Health check URLs verified
- [ ] Smoke test cases identified
- [ ] Critical API endpoints listed:
  1. _____
  2. _____
  3. _____

### Rollback Preparation

- [ ] Rollback script reviewed and tested
- [ ] Previous version identified: v_______
- [ ] Container images available for rollback
- [ ] Rollback procedure reviewed with team
- [ ] Rollback time estimate: ______ minutes
- [ ] Post-rollback steps documented

### Feature Flags

- [ ] Feature flags documented
- [ ] New features disabled in production
- [ ] Feature flag service operational
- [ ] Disable procedures tested
- [ ] New feature flags:
  1. _____
  2. _____

---

## Deployment Phase Execution

### Step 1: Final Confirmation (5 minutes before)

- [ ] All stakeholders ready
- [ ] Slack notification sent to team
- [ ] Support team standing by
- [ ] Time confirmed: ______

**Approved by**: _________________ **Date/Time**: _________

### Step 2: Backup & Freeze (if applicable)

- [ ] Database backup completed
- [ ] Configuration backed up
- [ ] Feature flags frozen
- [ ] Read replicas stopped (if any)

### Step 3: Deployment Execution

**Start Time**: _________

**Deployment Strategy**: Select one:

#### Blue-Green Deployment
- [ ] Green environment started
- [ ] Green environment health checks pass
- [ ] Database migrations run on green
- [ ] Traffic switched to green
- [ ] Blue environment retained for rollback

**Completion Time**: _________

#### Canary Deployment
- [ ] Canary phase 1 (5%) started at: _________
- [ ] Error rate within threshold
- [ ] Response time within threshold
- [ ] Canary phase 2 (25%) started at: _________
- [ ] Metrics still healthy
- [ ] Canary phase 3 (50%) started at: _________
- [ ] Canary phase 4 (100%) started at: _________

**Completion Time**: _________

#### Rolling Deployment
- [ ] Instance 1 updated at: _________
- [ ] Health check passed: [ ] Yes [ ] No
- [ ] Instance 2 updated at: _________
- [ ] Health check passed: [ ] Yes [ ] No
- [ ] Instance 3 updated at: _________
- [ ] Health check passed: [ ] Yes [ ] No

**Completion Time**: _________

#### Hotfix Deployment
- [ ] Hotfix branch verified: _________
- [ ] Quick tests passed
- [ ] Image built and deployed at: _________
- [ ] Smoke tests passed

**Completion Time**: _________

### Step 4: Immediate Verification (first 5 minutes)

- [ ] All containers running
- [ ] No restart loops observed
- [ ] CPU usage normal: ______ %
- [ ] Memory usage normal: ______ %
- [ ] Disk space available
- [ ] Database connections healthy
- [ ] Redis operational
- [ ] Log files clean (no errors)

---

## Post-Deployment Verification

### Phase 1: Infrastructure (first 5 minutes)

- [ ] No critical alerts triggered
- [ ] Error rate < 1%
- [ ] Response time < 2 seconds (p95)
- [ ] Database query time < 100ms (p95)
- [ ] Cache hit rate > 70%
- [ ] All services responding

### Phase 2: API Testing (5-15 minutes)

- [ ] Health endpoint responds: GET /api/health/ → 200
- [ ] Authentication works: POST /api/auth/login/ → 200
- [ ] Data endpoints accessible: GET /api/materials/ → 200
- [ ] WebSocket connects: wss://api.thebot.com/ws/ → 101
- [ ] No 500 errors in logs

### Phase 3: Frontend Testing (5-15 minutes)

- [ ] Homepage loads without errors
- [ ] Static assets (JS, CSS, images) load
- [ ] Forms submit successfully
- [ ] WebSocket real-time features work
- [ ] No console errors in browser

### Phase 4: User Acceptance Testing (15-30 minutes)

Test accounts to use:
- student@test.com / TestPass123!
- teacher@test.com / TestPass123!
- admin@test.com / TestPass123!

#### Student Workflow
- [ ] Can log in
- [ ] Can see dashboard
- [ ] Can access materials
- [ ] Can submit assignments
- [ ] Can view progress
- [ ] Can send chat messages

#### Teacher Workflow
- [ ] Can log in
- [ ] Can see class list
- [ ] Can grade assignments
- [ ] Can create lessons
- [ ] Can manage schedule
- [ ] Can respond to messages

#### Admin Workflow
- [ ] Can access admin panel
- [ ] Can manage users
- [ ] Can view analytics
- [ ] Can manage system settings

### Phase 5: Critical Features

- [ ] Payment system operational (YooKassa)
- [ ] Email notifications sending
- [ ] File uploads working
- [ ] Search functionality operational
- [ ] Reports generating correctly
- [ ] Export functionality working

### Phase 6: Performance Baseline

- [ ] Response time stable
- [ ] No memory leaks observed
- [ ] Database performance acceptable
- [ ] Cache working efficiently
- [ ] No unusual network traffic

### Phase 7: Security Verification

- [ ] HTTPS enforced
- [ ] Security headers present
- [ ] CORS configured correctly
- [ ] Authentication enforced
- [ ] No exposed sensitive data in logs
- [ ] No cross-site scripting vulnerabilities

---

## Monitoring Period

### First Hour Monitoring

**Start Time**: _________ **End Time**: _________

Monitor these metrics every 10 minutes:

| Time | Error Rate | Response Time | Database Time | Cache Hit | Action |
|------|-----------|-------|----------|------|--------|
| T+0  | _____ %   | _____ ms | _____ ms | _____ % | _________ |
| T+10 | _____ %   | _____ ms | _____ ms | _____ % | _________ |
| T+20 | _____ %   | _____ ms | _____ ms | _____ % | _________ |
| T+30 | _____ %   | _____ ms | _____ ms | _____ % | _________ |
| T+40 | _____ %   | _____ ms | _____ ms | _____ % | _________ |
| T+50 | _____ %   | _____ ms | _____ ms | _____ % | _________ |
| T+60 | _____ %   | _____ ms | _____ ms | _____ % | _________ |

### Issues Encountered

- [ ] None
- [ ] Minor (non-critical)
- [ ] Major (needs investigation)
- [ ] Critical (requires rollback)

If issues found:

**Issue Description**: _______________________________________________________

**Severity**: [ ] Minor [ ] Major [ ] Critical

**Root Cause**: ______________________________________________________________

**Resolution**: ________________________________________________________________

**Ticket Created**: #________

### Extended Monitoring (Next 24 Hours)

- [ ] Monitor at least every hour for first 4 hours
- [ ] Monitor every 4 hours for first 24 hours
- [ ] Watch for user complaints in support queue
- [ ] Monitor third-party integrations
- [ ] Check for data inconsistencies
- [ ] Verify no memory leaks over time

---

## Sign-Off and Documentation

### Deployment Sign-Off

| Role | Name | Time | Signature |
|------|------|------|-----------|
| DevOps Engineer | _________ | _____ | _________ |
| Tech Lead | _________ | _____ | _________ |
| QA Lead | _________ | _____ | _________ |
| Incident Commander | _________ | _____ | _________ |

### Status Update

- [ ] Status page updated to "Monitoring"
- [ ] Team notified of deployment completion
- [ ] Support team notified of any known issues
- [ ] Status page updated to "Operational"

### Documentation

- [ ] Deployment notes recorded
- [ ] Any deviations from plan documented
- [ ] Metrics baseline saved
- [ ] Logs collected for archive
- [ ] Post-incident review scheduled (if issues)

### Final Sign-Off

**Deployment Status**:
- [ ] Successful - All checks passed
- [ ] Successful - Minor issues, monitoring
- [ ] Partially Successful - Some rollback needed
- [ ] Failed - Full rollback executed

**Version Deployed**: v_______

**Deployment Completed At**: _________

**Next Scheduled Deployment**: _________

**Post-Incident Review Scheduled**: _________

---

## Rollback Checklist (if needed)

**Initiated At**: _________ **Completed At**: _________

**Reason for Rollback**: _________________________________________________________________

- [ ] Confirmed issue severity
- [ ] Notified all stakeholders
- [ ] Backed up current state
- [ ] Initiated rollback procedure
- [ ] Verified previous version operational
- [ ] Health checks passed
- [ ] Traffic fully switched back
- [ ] Verified user functionality
- [ ] Root cause analysis initiated
- [ ] Post-incident review scheduled

**Rollback Approved By**: _________________ **Time**: _________

---

## Notes

**DevOps Notes**:
_________________________________________________________________

**Tech Lead Notes**:
_________________________________________________________________

**QA Notes**:
_________________________________________________________________

**Incident Notes** (if applicable):
_________________________________________________________________

---

**Checklist Completed By**: _________________ **Date**: _________

**For Future Reference**: Archive this checklist at `deployment-logs/v___-<date>.md`
