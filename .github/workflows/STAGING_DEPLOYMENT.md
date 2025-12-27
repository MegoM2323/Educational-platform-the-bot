# CD Pipeline Staging Deployment Guide

## Overview

The **CD Pipeline Staging** workflow provides continuous deployment to the staging environment. It automatically triggers when the CI build pipeline succeeds on the `develop` branch, pulling the latest Docker images and deploying them with comprehensive health checks and smoke tests.

## Trigger Events

The deployment pipeline can be triggered by:

1. **Build Success** (Automatic)
   - Runs after successful completion of the `CI Pipeline Build` workflow
   - Only on `develop` branch
   - Pulls latest Docker images from GHCR

2. **Manual Trigger** (workflow_dispatch)
   - Run deployment manually through GitHub Actions UI
   - Select environment: `staging` or `staging-test`
   - Useful for hotfixes or manual deployments

3. **Configuration Changes** (push)
   - Triggers when deployment configuration changes:
     - `.github/workflows/deploy-staging.yml`
     - `docker-compose.yml`

## Deployment Architecture

### Phase 1: Prepare Staging Environment
- **Job**: `prepare`
- **Duration**: ~2-3 minutes
- **Actions**:
  - Generate deployment ID and timestamp
  - Determine Docker image references
  - Create GitHub deployment record
  - Output image tags for downstream jobs

### Phase 2: Pre-deployment Validation
- **Job**: `validate`
- **Duration**: ~3-5 minutes
- **Actions**:
  - Log in to GitHub Container Registry (GHCR)
  - Verify backend image exists and is pullable
  - Verify frontend image exists and is pullable
  - Validate docker-compose.yml configuration
  - Check deployment prerequisites (SSH secrets)
  - Ensure required GitHub secrets are configured

### Phase 3: Deploy to Staging
- **Job**: `deploy`
- **Duration**: ~10-15 minutes
- **Environment**: Protected with staging approval requirements
- **Actions**:
  1. Setup SSH connection to staging server
  2. Create deployment manifest with metadata
  3. Copy docker-compose.yml and manifest to staging
  4. Pull Docker images from GHCR
  5. Stop old containers gracefully
  6. Start new services with docker-compose
  7. Run database migrations
  8. Collect static files
  9. Create deployment info JSON
  10. Upload deployment manifest as artifact

### Phase 4: Health Checks
- **Job**: `health-check`
- **Duration**: ~3-5 minutes (with retries)
- **Configuration**:
  - Retries: 15 attempts
  - Interval: 5 seconds between attempts
  - Timeout: 75 seconds total
- **Checks**:
  - Backend health endpoint: `/api/system/health/`
  - Frontend availability: `/`
  - Service connectivity: `/api/system/readiness/`

### Phase 5: Smoke Tests
- **Job**: `smoke-tests`
- **Duration**: ~5-10 minutes
- **Test Coverage**:
  1. API availability
  2. Frontend availability (content check)
  3. Authentication endpoints
  4. Static files endpoint
  5. Database connectivity (via API)
  6. Critical endpoints (health, login, profile)

### Phase 6: Rollback on Failure
- **Job**: `rollback`
- **Duration**: ~2-3 minutes
- **Trigger**: Only if deployment fails
- **Actions**:
  - Fetch previous commit from origin
  - Revert to previous deployment
  - Restart services with previous configuration

### Phase 7: Notifications
- **Job**: `notify`
- **Duration**: ~1-2 minutes
- **Notification Channels**:
  - Telegram (deployment status)
  - GitHub deployment status (for tracking)
  - PR comments (if triggered from PR)
  - Artifacts upload (logs and manifests)
  - GitHub summary (workflow summary)

## Required Secrets

Configure these secrets in GitHub repository settings:

### SSH Credentials
- `STAGING_SSH_KEY`: Private SSH key for staging server access (openssh format)
- `STAGING_HOST`: Staging server hostname/IP (e.g., `staging.example.com`)
- `STAGING_USER`: SSH username (e.g., `deploy`)
- `STAGING_PATH`: Deployment path on server (e.g., `/home/deploy/the-bot`)

### Notifications
- `TELEGRAM_BOT_TOKEN`: Telegram bot token for notifications
- `TELEGRAM_LOG_CHAT_ID`: Telegram chat ID for deployment logs

### Authentication
- `GITHUB_TOKEN`: Automatically provided by GitHub Actions

## Environment Configuration

The staging server requires:

### `.env.staging` file
Create on staging server at `${STAGING_PATH}/.env.staging`:

```bash
# Core
ENVIRONMENT=staging
DEBUG=False
SECRET_KEY=your-secret-key-min-50-chars

# Database (copy from production or use separate)
DATABASE_URL=postgresql://user:password@postgres-host/thebot_staging

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=your-redis-password

# Frontend
FRONTEND_URL=https://staging.the-bot.ru

# API Configuration
API_URL=https://staging.the-bot.ru/api

# External Services
YOOKASSA_SHOP_ID=your-shop-id
YOOKASSA_SECRET_KEY=your-secret-key
OPENROUTER_API_KEY=your-key
PACHCA_FORUM_API_TOKEN=your-token
TELEGRAM_BOT_TOKEN=your-token

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email
EMAIL_HOST_PASSWORD=your-password
```

### Docker Compose Configuration
The pipeline uses `docker-compose.yml` which includes:
- PostgreSQL database service
- Redis cache service
- Backend API service
- Frontend service
- Monitoring stack (optional)

## Deployment Process

### Step-by-Step Flow

1. **Trigger CI Build**
   ```bash
   git push origin develop
   # or manually create release/tag
   ```

2. **CI Build Pipeline Runs**
   - Builds backend and frontend images
   - Tags images as `backend:${COMMIT_SHA}` and `frontend:${COMMIT_SHA}`
   - Pushes images to GHCR
   - Runs tests and security scans

3. **CD Staging Pipeline Triggers**
   - Automatically starts after successful CI build
   - Validates images exist in GHCR
   - Deploys to staging environment

4. **Deployment Verification**
   - Health checks confirm services are running
   - Smoke tests verify functionality
   - Notifications sent to team

5. **Manual Testing**
   - Access staging: https://staging.the-bot.ru
   - Run manual E2E tests if needed
   - Monitor logs: `docker-compose logs -f`

### Manual Deployment

To manually deploy without CI build:

1. Go to GitHub Actions
2. Select "CD Pipeline Staging" workflow
3. Click "Run workflow"
4. Select environment (staging or staging-test)
5. Click "Run workflow"

## Monitoring Deployment

### View Logs
```bash
# SSH into staging server
ssh ${STAGING_USER}@${STAGING_HOST}

# View docker-compose logs
cd ${STAGING_PATH}
docker-compose logs -f

# View specific service
docker-compose logs -f backend
docker-compose logs -f frontend

# View migration logs
docker-compose logs backend | grep -i migration
```

### Check Deployment Status
```bash
# Verify services are running
docker-compose ps

# Check image tags
docker image ls | grep thebot

# View deployment info
cat deployment-info.json
```

### Health Endpoints
- Backend: https://staging.the-bot.ru/api/system/health/
- Readiness: https://staging.the-bot.ru/api/system/readiness/
- Metrics: https://staging.the-bot.ru/api/system/metrics/

## Rollback Procedure

### Automatic Rollback
- Triggers automatically if deployment fails health checks
- Reverts to previous commit and restarts services

### Manual Rollback
```bash
# SSH into staging server
ssh ${STAGING_USER}@${STAGING_HOST}
cd ${STAGING_PATH}

# Stop current deployment
docker-compose down

# Revert to previous version
git fetch origin develop
git checkout develop
git reset --hard HEAD~1

# Restart services
docker-compose up -d
```

## Troubleshooting

### Image Not Found
**Error**: "Backend image not found: ghcr.io/.../backend:sha..."

**Solution**:
1. Ensure CI build completed successfully
2. Check image exists: `docker pull ghcr.io/.../backend:${SHA}`
3. Verify GITHUB_TOKEN has package access

### Health Check Failed
**Error**: "Backend health check failed after 15 attempts"

**Solution**:
1. SSH to staging and check logs: `docker-compose logs backend`
2. Verify database migrations completed
3. Check environment variables in `.env.staging`
4. Verify network connectivity

### SSH Connection Failed
**Error**: "Permission denied (publickey)"

**Solution**:
1. Verify STAGING_SSH_KEY secret is configured
2. Ensure SSH key is in OpenSSH format: `ssh-keygen -p -f key -m pem -N ""`
3. Check STAGING_HOST is correct
4. Verify staging server has public key installed

### Docker Compose Fails
**Error**: "docker-compose command not found"

**Solution**:
1. SSH to staging server
2. Install docker-compose: `pip install docker-compose`
3. Or use docker compose (v2): `docker compose up -d`

## Performance Optimization

### Image Pull Times
- Images cached on staging server
- Subsequent deployments pull faster
- Large images may take 5-10 minutes on first pull

### Database Migrations
- Run in background during deployment
- Typically 30-60 seconds for typical schema changes
- Monitor migration status: `docker-compose logs backend`

### Smoke Test Duration
- 5-10 minutes for full test suite
- Can be optimized by reducing test cases
- See PHASE 5 in deploy-staging.yml

## Best Practices

1. **Test Before Deploying**
   - Always run tests locally before pushing
   - Ensure CI build passes all checks

2. **Review Deployment Logs**
   - Check GitHub Actions logs for errors
   - Review staging server logs after deployment
   - Monitor for any warnings or issues

3. **Manual Testing**
   - Always do manual smoke tests on staging
   - Test critical user journeys
   - Verify data integrity after migrations

4. **Database Safety**
   - Backup staging database before migration
   - Migrations are reversible (use Django migrations)
   - Test migrations locally first

5. **Notification Handling**
   - Monitor Telegram notifications
   - Set up alerts for failed deployments
   - Review deployment summaries

## Deployment Artifacts

The following artifacts are generated for each deployment:

### Generated Files
- **staging-deployment-manifest/**: Deployment configuration and image references
- **staging-deployment-logs/**: Deployment logs and info JSON
- **build-report/**: Build details and image tags (from CI pipeline)

### Retention
- Artifacts kept for 30 days
- Can be downloaded from GitHub Actions
- Used for audit trail and troubleshooting

## CI/CD Integration

### Upstream: CI Pipeline Build
- Builds Docker images
- Runs linting and security checks
- Pushes images to GHCR
- Publishes test results

### This Pipeline: CD Staging
- Pulls images from GHCR
- Validates and deploys to staging
- Runs health checks and smoke tests
- Notifies team of status

### Downstream: Manual Testing & Production Deploy
- Manual E2E tests on staging
- Code review and approval
- Manual production deployment trigger

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [SSH Key Setup](https://docs.github.com/en/authentication/connecting-to-github-with-ssh)
- [Container Registry (GHCR)](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
