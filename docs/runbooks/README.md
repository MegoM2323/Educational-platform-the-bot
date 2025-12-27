# THE_BOT Platform - Deployment Runbooks

Complete operational runbooks for deploying THE_BOT platform with comprehensive procedures for pre-deployment checks, multiple deployment strategies, rollback procedures, and post-deployment verification.

## Quick Navigation

### Main Documentation

1. **[DEPLOYMENT.md](./DEPLOYMENT.md)** - Main deployment runbook
   - Overview and deployment timeline
   - Pre-deployment checklist
   - Four deployment strategies (Blue-Green, Canary, Rolling, Hotfix)
   - Rollback procedures
   - Database migrations
   - Post-deployment verification
   - Monitoring and alerts
   - Troubleshooting guide

2. **[DEPLOYMENT_STRATEGIES.md](./DEPLOYMENT_STRATEGIES.md)** - Detailed strategy guides
   - Step-by-step implementation for each strategy
   - Code examples for each approach
   - Decision tree for choosing strategy
   - Strategy comparison matrix

3. **[templates/deployment-checklist.md](./templates/deployment-checklist.md)** - Pre-deployment checklist
   - Comprehensive checklist template
   - Deployment information section
   - Pre-deployment phase checks
   - Deployment phase tracking
   - Post-deployment verification
   - Sign-off documentation

### Deployment Scripts

Located in `scripts/deployment/`:

1. **[pre-deploy-check.sh](../../scripts/deployment/pre-deploy-check.sh)** - Pre-deployment validation
   - Git repository status
   - Environment configuration
   - Docker setup verification
   - Code quality checks
   - Dependency security scanning
   - Database connectivity
   - Test suite validation
   - SSL certificate checks

2. **[rollback.sh](../../scripts/deployment/rollback.sh)** - Emergency rollback
   - Zero-downtime rollback
   - Database backup before rollback
   - Configuration archiving
   - Incident documentation
   - Team notifications
   - Automatic verification

3. **[verify-deployment.sh](../../scripts/deployment/verify-deployment.sh)** - Post-deployment verification
   - Infrastructure health checks
   - Connectivity verification
   - API endpoint testing
   - Performance monitoring
   - Error rate checking
   - Database and Redis verification

---

## Deployment Workflow

### Standard Deployment Process

```
1. PRE-DEPLOYMENT (5-10 minutes)
   ├─ Run: ./scripts/deployment/pre-deploy-check.sh
   ├─ Review: docs/runbooks/templates/deployment-checklist.md
   └─ Complete all checks

2. CHOOSE STRATEGY
   ├─ Regular release? → Blue-Green (recommended)
   ├─ Major change? → Canary deployment
   ├─ Multiple instances? → Rolling update
   └─ Critical bug? → Hotfix deployment

3. EXECUTE DEPLOYMENT
   ├─ Follow strategy guide from DEPLOYMENT_STRATEGIES.md
   ├─ Monitor metrics during rollout
   └─ Keep rollback.sh ready

4. POST-DEPLOYMENT (5-15 minutes)
   ├─ Run: ./scripts/deployment/verify-deployment.sh
   ├─ Monitor for 1 hour minimum
   └─ Check all systems operational

5. SIGN-OFF & DOCUMENTATION
   ├─ Complete deployment checklist
   ├─ Document any issues
   └─ Archive logs
```

---

## Deployment Strategies at a Glance

### Blue-Green Deployment (Recommended)

**Best for**: Regular feature releases, non-breaking changes

- **Duration**: 10-15 minutes
- **Downtime**: 0 seconds
- **Rollback**: <1 minute
- **Resources**: 2x
- **Risk**: Low

**Quick Start**:
```bash
# 1. Check everything
./scripts/deployment/pre-deploy-check.sh

# 2. Follow Blue-Green section in DEPLOYMENT_STRATEGIES.md
# 3. Verify
./scripts/deployment/verify-deployment.sh
```

### Canary Deployment

**Best for**: Major feature changes, database schema changes

- **Duration**: 30-45 minutes
- **Downtime**: 0 seconds
- **Rollback**: 2-5 minutes
- **Resources**: 1.5x
- **Risk**: Very Low

**Quick Start**:
```bash
# 1. Check everything
./scripts/deployment/pre-deploy-check.sh

# 2. Follow Canary section in DEPLOYMENT_STRATEGIES.md
# 3. Monitor at each phase (5% → 25% → 50% → 100%)
```

### Rolling Update

**Best for**: Microservice deployments, multiple instances

- **Duration**: 20-40 minutes
- **Downtime**: 0 seconds
- **Rollback**: 3-10 minutes
- **Resources**: 1x
- **Risk**: Medium

**Quick Start**:
```bash
# 1. Check everything
./scripts/deployment/pre-deploy-check.sh

# 2. Follow Rolling Update section in DEPLOYMENT_STRATEGIES.md
# 3. Update instances one by one
```

### Hotfix Deployment (Emergency)

**Best for**: Critical production bugs only

- **Duration**: <5 minutes
- **Downtime**: ~30 seconds
- **Rollback**: <1 minute
- **Resources**: 1x
- **Risk**: High

**Quick Start**:
```bash
#!/bin/bash
# ONLY FOR CRITICAL PRODUCTION BUGS

# 1. Git checkout hotfix branch
git checkout hotfix/critical-bug

# 2. Quick tests
npm run test:critical

# 3. Build
docker build -t thebot:hotfix backend/

# 4. Deploy (minimal verification)
docker-compose -f docker-compose.prod.yml up -d backend

# 5. Verify
./scripts/deployment/verify-deployment.sh

# 6. Monitor closely
```

---

## Key Scripts Reference

### Pre-Deployment Check

```bash
# Standard usage
./scripts/deployment/pre-deploy-check.sh

# Skip tests (faster)
./scripts/deployment/pre-deploy-check.sh --no-tests

# Quick checks only
./scripts/deployment/pre-deploy-check.sh --quick

# Verbose output
./scripts/deployment/pre-deploy-check.sh --verbose
```

**Checks performed**:
- Git status and commits
- Environment variables (SECRET_KEY, DATABASE_URL, etc.)
- Docker installation and health
- Code style (black, eslint)
- Type checking (mypy)
- Security vulnerabilities (pip-audit, npm audit)
- Database connectivity
- Test suite (pytest, npm test)
- SSL certificates
- Pending migrations
- nginx configuration

**Exit codes**:
- 0: All checks passed, deployment ready
- 1: Some checks failed, do not deploy

### Rollback Script

```bash
# Rollback to previous version
./scripts/deployment/rollback.sh

# Rollback to specific version
./scripts/deployment/rollback.sh v1.2.3

# Dry run (see what would happen)
./scripts/deployment/rollback.sh --dry-run

# Skip verification (emergency only)
./scripts/deployment/rollback.sh --no-verify
```

**What it does**:
1. Backs up current database and configuration
2. Saves logs for post-incident analysis
3. Checks out previous version
4. Starts service with previous version
5. Runs health checks
6. Creates incident report
7. Notifies team

**Exit codes**:
- 0: Rollback successful
- 1: Rollback failed, manual intervention needed
- 2: Critical error during rollback

### Verification Script

```bash
# Full verification (recommended)
./scripts/deployment/verify-deployment.sh

# Quick checks only
./scripts/deployment/verify-deployment.sh --quick

# Strict mode (fail on any issue)
./scripts/deployment/verify-deployment.sh --strict

# Check specific environment
./scripts/deployment/verify-deployment.sh --env green

# Custom timeout
./scripts/deployment/verify-deployment.sh --timeout 60
```

**What it checks**:
- Container status and health
- Database and Redis connectivity
- API endpoints responding
- Frontend page loads
- WebSocket connections
- Error rates
- Response times
- Disk space
- Memory usage
- Migration status
- Static file serving

**Exit codes**:
- 0: All checks passed
- 1: Some checks failed
- 2: Critical checks failed (rollback required)

---

## Pre-Deployment Checklist Sections

### 1. Team Readiness
- DevOps engineer assigned
- Tech lead assigned
- QA engineer assigned
- Support team notified
- Stakeholders informed

### 2. Code Quality
- All tests passing
- Code review completed
- Security scan passed
- No critical CVEs
- Linting passed
- Type checking passed

### 3. Environment
- `.env.production` exists
- All required variables set
- SECRET_KEY strong (50+ chars)
- No sensitive data in git

### 4. Database
- Database backed up
- Replication healthy
- Slow query log enabled
- Migrations tested

### 5. Infrastructure
- Docker images built
- Docker registry accessible
- SSL certificates valid (>30 days)
- Load balancer configured
- Rate limiting set up

### 6. Monitoring
- Prometheus targets verified
- Alert rules configured
- Grafana dashboards ready
- Log aggregation online
- Baseline metrics captured

### 7. Post-Deployment
- Health checks prepared
- Verification script ready
- Rollback procedure documented
- Team on standby

---

## Emergency Procedures

### If Something Goes Wrong During Deployment

```bash
# 1. STOP - Don't continue
echo "STOPPING DEPLOYMENT"

# 2. Check what's wrong
./scripts/deployment/verify-deployment.sh

# 3. Assess severity
# - Critical (>5% error rate, API down) → Rollback immediately
# - Major (>2% error rate) → Investigate quickly
# - Minor (<1% error rate) → Monitor closely

# 4. If critical, rollback immediately
./scripts/deployment/rollback.sh

# 5. Contact team
# - Post in #incidents Slack channel
# - Call incident commander
# - Create incident ticket

# 6. After rollback
# - Root cause analysis
# - Fix implementation
# - Re-test in staging
# - Re-deploy with canary strategy
```

### Rollback Decision Tree

```
Issue Detected
├─ API returning 500s (>5%)
│  └─ → IMMEDIATE ROLLBACK REQUIRED
├─ High error rate (2-5%)
│  └─ → INVESTIGATE then ROLLBACK if not resolved in 2 mins
├─ Slow responses (>2s p95)
│  └─ → MONITOR for 5 min, then ROLLBACK if not improving
├─ WebSocket down
│  └─ → IMMEDIATE ROLLBACK REQUIRED
├─ Database issues
│  └─ → Restore from backup + rollback code
└─ Minor issues (<1%)
   └─ → MONITOR closely but continue observing
```

---

## Monitoring Post-Deployment

### Critical Metrics

Monitor these for **at least 1 hour** after deployment:

| Metric | Threshold | Action |
|--------|-----------|--------|
| Error Rate | >1% | Investigate |
| Error Rate | >5% | Rollback immediately |
| Response Time (p95) | >2s | Investigate |
| Response Time (p95) | >5s | Rollback immediately |
| Database Response | >100ms | Check queries |
| Cache Hit Rate | <70% | Warmup cache |
| WebSocket Connections | Spike/Drop | Investigate Redis |
| CPU Usage | >80% | Check for leaks |
| Memory Usage | >80% | Check for leaks |

### Monitoring Timeline

```
T+0 min    Deployment completes
T+0-5 min  CRITICAL monitoring (1 min intervals)
           Alert threshold: Error rate > 5%

T+5-30 min INTENSIVE monitoring (5 min intervals)
           Alert threshold: Error rate > 2%

T+30-60 min NORMAL monitoring (10 min intervals)
           Alert threshold: Error rate > 1%

T+1-24 hrs EXTENDED monitoring (every 30 min)
           Alert threshold: Normal baseline
```

---

## Detailed Documentation Location

- **Main Deployment Guide**: [DEPLOYMENT.md](./DEPLOYMENT.md)
  - Comprehensive runbook
  - All deployment strategies
  - Rollback procedures
  - Database migration strategies
  - Troubleshooting guide

- **Strategy Implementation**: [DEPLOYMENT_STRATEGIES.md](./DEPLOYMENT_STRATEGIES.md)
  - Step-by-step guides
  - Code examples
  - Implementation details
  - Decision trees

- **Checklist Template**: [templates/deployment-checklist.md](./templates/deployment-checklist.md)
  - Fill-in checklist form
  - Sign-off section
  - Evidence tracking
  - Deployment log

---

## Common Deployment Scenarios

### Scenario 1: Regular Feature Release

```bash
# 1. Pre-deployment
./scripts/deployment/pre-deploy-check.sh

# 2. Use Blue-Green (safest for regular releases)
# Follow: DEPLOYMENT_STRATEGIES.md → Blue-Green section

# 3. Verify
./scripts/deployment/verify-deployment.sh

# 4. Monitor
# Check Grafana every 10 minutes for 1 hour
```

### Scenario 2: Critical Database Change

```bash
# 1. Extra pre-deployment checks
./scripts/deployment/pre-deploy-check.sh

# 2. Backup database
docker-compose exec postgres pg_dump -U postgres -F c \
  -f /backups/critical_change_$(date +%s).dump thebot_db

# 3. Use Canary deployment
# Follow: DEPLOYMENT_STRATEGIES.md → Canary section

# 4. Extend monitoring to 2+ hours
# Database changes often show issues later
```

### Scenario 3: Production Emergency

```bash
# 1. IMMEDIATELY rollback current deployment
./scripts/deployment/rollback.sh

# 2. Contact incident commander
# Post in #incidents, call team

# 3. Root cause analysis
# Review logs, metrics, recent changes

# 4. Create hotfix
git checkout -b hotfix/critical-bug main

# 5. Fix the issue (minimal changes only)

# 6. Test thoroughly
npm run test:critical
pytest tests/critical/ -v

# 7. Deploy as hotfix
./scripts/deployment/deploy-hotfix.sh

# 8. Monitor closely for 2 hours
```

### Scenario 4: Blue-Green Rollback

```bash
# If blue-green deployment goes wrong:
./scripts/deployment/rollback.sh

# Blue environment is kept running
# Instant rollback by switching nginx upstream
# Takes <1 minute

# Then investigate root cause
```

---

## Deployment Troubleshooting

For common issues and solutions, see [DEPLOYMENT.md#troubleshooting](./DEPLOYMENT.md#troubleshooting).

### Quick Reference

- **Docker image pull fails**: Check registry credentials
- **Database migration fails**: Review migration SQL, test on staging
- **Services in restart loop**: Check logs, memory, environment variables
- **Performance degradation**: Check slow query log, cache hit rates
- **WebSocket connection fails**: Verify Redis connectivity

---

## Getting Help

### If Something Goes Wrong

1. **Immediate**: Execute rollback
   ```bash
   ./scripts/deployment/rollback.sh
   ```

2. **Document**: Check logs
   ```bash
   docker logs thebot-backend-prod | tail -100
   ```

3. **Investigate**: Review metrics
   - Grafana: https://grafana.thebot.com
   - Logs: https://logs.thebot.com
   - Error tracking: https://sentry.thebot.com

4. **Report**: Create incident ticket
   - Title: [INCIDENT] Deployment issue - v1.2.3
   - Include: Error logs, metrics, rollback proof

5. **Learn**: Post-incident review
   - What went wrong?
   - Why wasn't it caught pre-deployment?
   - How do we prevent it next time?

---

## Compliance & Audit

All deployments should be:
- **Documented**: Use deployment checklist
- **Verified**: Run verification script
- **Monitored**: Keep metrics for 1+ hour
- **Logged**: Archive logs and reports
- **Signed-off**: Get approvals before deployment

Deployment logs are archived at: `deployment-logs/`

---

## Contact & Support

- **DevOps Team**: devops@thebot.com
- **On-Call**: Check team calendar for on-call schedule
- **Incident Commander**: [On-call person]
- **Status Page**: https://status.thebot.com

---

## Document Information

- **Version**: 1.0.0
- **Last Updated**: 2025-12-27
- **Maintained by**: DevOps Team
- **Review Schedule**: Quarterly or after major incidents

## Files in This Directory

```
docs/runbooks/
├── README.md (this file)
├── DEPLOYMENT.md (main runbook - 800+ lines)
├── DEPLOYMENT_STRATEGIES.md (strategy guides - 700+ lines)
└── templates/
    └── deployment-checklist.md (checklist template)

scripts/deployment/
├── pre-deploy-check.sh (validation script - 500+ lines)
├── rollback.sh (emergency rollback - 400+ lines)
├── verify-deployment.sh (post-deploy verification - 450+ lines)
└── deploy_server_config.sh (existing server config)
```

---

**Ready to deploy? Start here**:
1. Read: [DEPLOYMENT.md](./DEPLOYMENT.md) overview section
2. Check: Run `./scripts/deployment/pre-deploy-check.sh`
3. Plan: Fill out [deployment-checklist.md](./templates/deployment-checklist.md)
4. Execute: Follow your chosen strategy from [DEPLOYMENT_STRATEGIES.md](./DEPLOYMENT_STRATEGIES.md)
5. Verify: Run `./scripts/deployment/verify-deployment.sh`
6. Monitor: Watch metrics for 1+ hour

**Questions?** See the troubleshooting sections or contact the DevOps team.
