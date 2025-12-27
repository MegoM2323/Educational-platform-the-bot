# CI Pipeline Build - Test Plan

## Test Scope

This document outlines the comprehensive test plan for the CI Pipeline Build (T_DEV_005).

### Components Under Test

1. GitHub Actions workflow: `.github/workflows/build.yml`
2. Backend Docker image build process
3. Frontend Docker image build process
4. Image tagging and registry integration
5. Artifact generation and storage
6. Security scanning integration

## Test Categories

### 1. Workflow Trigger Tests

#### Test 1.1: Push to Main Branch

**Condition**: Push to `main` branch

**Expected Behavior**:
- Workflow triggers automatically
- All 6 jobs execute in sequence
- Backend and frontend build in parallel
- Images tagged with: `latest`, `{sha}`, `main`
- Images pushed to GHCR

**Verification**:
```bash
# Check GitHub Actions logs
gh workflow view build.yml

# Verify images in GHCR
gh api repos/{owner}/{repo}/packages | jq '.[] | select(.package_type=="container")'
```

#### Test 1.2: Push to Develop Branch

**Condition**: Push to `develop` branch

**Expected Behavior**:
- Workflow triggers automatically
- Images tagged with: `develop`, `{sha}`
- Images do NOT push to registry (develop only on main/release)

**Verification**:
```bash
# Check workflow logs show no push
gh run list --workflow=build.yml | grep develop
```

#### Test 1.3: Create Release Tag

**Condition**: Create tag matching `v*` pattern (e.g., `v1.0.0`)

**Expected Behavior**:
- Workflow triggers
- Images tagged with: `latest`, `{sha}`, `v1.0.0`
- Images pushed to GHCR
- Release information created

**Verification**:
```bash
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0

# Verify in GitHub UI
gh release view v1.0.0
```

#### Test 1.4: Pull Request

**Condition**: Open PR to `main` or `develop`

**Expected Behavior**:
- Workflow triggers
- Images build locally (no push to registry)
- PR comment created with build status
- Artifacts available for download

**Verification**:
```bash
# Check PR comments for build status
gh pr view {pr-number} --json comments
```

#### Test 1.5: Manual Workflow Trigger

**Condition**: Dispatch workflow manually

**Expected Behavior**:
- Workflow starts on demand
- Optional: push_to_registry parameter respected

**Verification**:
```bash
# Trigger manually
gh workflow run build.yml

# Verify execution
gh run list --workflow=build.yml
```

### 2. Build Metadata Tests

#### Test 2.1: Version Determination

**Condition**: Different git states

**Test Cases**:

| Git State | Expected Version | Is Release |
|-----------|------------------|-----------|
| On tag v1.0.0 | v1.0.0 | true |
| On main branch | dev+hash | false |
| On feature branch | dev+hash | false |
| Detached HEAD | dev+hash | false |

**Verification**:
```bash
# Check step outputs
gh run view {run-id} --json jobs | jq '.jobs[] | select(.name=="Setup Build Metadata")'
```

#### Test 2.2: Build Date Timestamp

**Condition**: Workflow execution

**Expected Behavior**:
- ISO 8601 format: `2025-01-15T10:30:45Z`
- UTC timezone
- Consistent across all jobs

**Verification**:
```bash
# Check workflow logs
gh run view {run-id} --log | grep "Build Date:"
```

#### Test 2.3: Git SHA Extraction

**Condition**: Workflow execution

**Expected Behavior**:
- Full 40-character SHA
- Matches `github.sha` context
- Used in image tags

**Verification**:
```bash
# Verify git SHA
git rev-parse HEAD

# Compare with workflow output
gh run view {run-id} --json jobs | jq '.jobs[] | select(.name=="Setup Build Metadata").steps'
```

#### Test 2.4: Image Tag Generation

**Condition**: Different trigger scenarios

**Test Cases**:

```
Main branch:
  backend: ghcr.io/owner/repo/backend:latest
          ghcr.io/owner/repo/backend:{sha}
          ghcr.io/owner/repo/backend:main
  frontend: ghcr.io/owner/repo/frontend:latest
           ghcr.io/owner/repo/frontend:{sha}
           ghcr.io/owner/repo/frontend:main

Develop branch:
  backend: ghcr.io/owner/repo/backend:develop
          ghcr.io/owner/repo/backend:{sha}
  frontend: ghcr.io/owner/repo/frontend:develop
           ghcr.io/owner/repo/frontend:{sha}

Release (v1.0.0):
  backend: ghcr.io/owner/repo/backend:latest
          ghcr.io/owner/repo/backend:{sha}
          ghcr.io/owner/repo/backend:v1.0.0
  frontend: ghcr.io/owner/repo/frontend:latest
           ghcr.io/owner/repo/frontend:{sha}
           ghcr.io/owner/repo/frontend:v1.0.0
```

**Verification**:
```bash
# Check IMAGE_TAGS.json artifact
gh run download {run-id} -n build-report
cat IMAGE_TAGS.json | jq '.'
```

### 3. Backend Build Tests

#### Test 3.1: Docker Image Builds Successfully

**Condition**: Backend Docker build

**Expected Behavior**:
- Build completes within 5 minutes (with cache)
- No build errors
- Image created successfully
- Multi-platform support verified

**Verification**:
```bash
# Check build logs
gh run view {run-id} --json jobs | jq '.jobs[] | select(.name=="Build Backend Image")'

# Pull and test image locally
docker pull ghcr.io/owner/repo/backend:{sha}
docker inspect ghcr.io/owner/repo/backend:{sha}
```

#### Test 3.2: Python Dependencies Installed

**Condition**: Backend Docker build

**Expected Behavior**:
- All requirements.txt packages installed
- No build errors
- Virtual environment created
- Wheels cached for reuse

**Verification**:
```bash
# Run container and check python packages
docker run ghcr.io/owner/repo/backend:{sha} \
  pip list | grep -E "Django|djangorestframework|celery"
```

#### Test 3.3: Multi-Platform Build

**Condition**: Backend Docker build

**Expected Behavior**:
- Builds for linux/amd64
- Builds for linux/arm64
- No architecture-specific errors

**Verification**:
```bash
# Check build logs for platform mentions
gh run view {run-id} --log | grep -i "platform\|amd64\|arm64"
```

#### Test 3.4: Dockerfile Layer Caching

**Condition**: Consecutive backend builds on same branch

**Expected Behavior**:
- Second build faster than first (if no code changes)
- Cache layers reused
- Build time reduced significantly

**Verification**:
```bash
# Compare build times from workflow logs
# First run: ~5 minutes
# Second run: ~2 minutes (with cache)
```

#### Test 3.5: Health Check Configuration

**Condition**: Backend image creation

**Expected Behavior**:
- Health check configured
- Checks `/api/system/health/` endpoint
- 30-second interval
- 10-second timeout

**Verification**:
```bash
docker inspect ghcr.io/owner/repo/backend:{sha} | \
  jq '.[] | .Config.Healthcheck'
```

#### Test 3.6: Non-root User

**Condition**: Backend image runtime

**Expected Behavior**:
- Runs as appuser (UID 1001)
- Not as root (UID 0)
- Proper file permissions

**Verification**:
```bash
docker run --rm ghcr.io/owner/repo/backend:{sha} whoami
# Expected output: appuser
```

### 4. Frontend Build Tests

#### Test 4.1: React Build Completes

**Condition**: Frontend Docker build

**Expected Behavior**:
- npm ci succeeds
- npm run build succeeds
- dist directory created
- Build completes within 5 minutes

**Verification**:
```bash
# Check build logs
gh run view {run-id} --json jobs | \
  jq '.jobs[] | select(.name=="Build Frontend Image")'

# Verify image
docker pull ghcr.io/owner/repo/frontend:{sha}
docker run --rm ghcr.io/owner/repo/frontend:{sha} ls -la /usr/share/nginx/html/
```

#### Test 4.2: Vite Build Optimization

**Condition**: Frontend Docker build

**Expected Behavior**:
- Tree-shaking enabled
- Minification applied
- Code splitting configured
- Bundle size < 250KB gzipped

**Verification**:
```bash
# Extract and check dist directory
docker run --rm ghcr.io/owner/repo/frontend:{sha} \
  find /usr/share/nginx/html -name "*.js" -type f | wc -l

# Estimate gzip size
docker run --rm ghcr.io/owner/repo/frontend:{sha} \
  sh -c "gzip -c /usr/share/nginx/html/index.html | wc -c"
```

#### Test 4.3: Nginx Configuration

**Condition**: Frontend image creation

**Expected Behavior**:
- Nginx configured
- Health check configured
- Serves on port 3000 (mapped from 80)
- SPA routing configured

**Verification**:
```bash
docker inspect ghcr.io/owner/repo/frontend:{sha} | \
  jq '.[] | select(.Config.ExposedPorts)'
```

#### Test 4.4: NPM Cache Effectiveness

**Condition**: Consecutive frontend builds on same branch

**Expected Behavior**:
- npm ci faster on repeated runs
- node_modules cache hit
- Dependency installation time reduced

**Verification**:
```bash
# Check workflow logs for cache hit/miss
gh run view {run-id} --log | grep -i "cache\|npm"
```

#### Test 4.5: Environment Variables

**Condition**: Frontend Docker build with environment variables

**Expected Behavior**:
- VITE_DJANGO_API_URL injected into build
- VITE_WEBSOCKET_URL injected into build
- Variables available in frontend code

**Verification**:
```bash
# Check build args in Docker logs
gh run view {run-id} --log | grep -i "VITE_"
```

### 5. Image Registry Tests

#### Test 5.1: Images Pushed to GHCR

**Condition**: Push to main or release tag

**Expected Behavior**:
- Images appear in ghcr.io registry
- Available within 5 minutes of push
- Multiple tags available

**Verification**:
```bash
# Check GHCR
docker pull ghcr.io/owner/repo/backend:latest
docker pull ghcr.io/owner/repo/frontend:latest

# Via GitHub CLI
gh api repos/{owner}/{repo}/packages --jq '.[] | .name'
```

#### Test 5.2: Image Pull Access

**Condition**: Pulling from GHCR

**Expected Behavior**:
- Images pullable with GITHUB_TOKEN
- Or public if repository is public
- Images fully downloaded
- No corruption

**Verification**:
```bash
# Pull with authentication
echo $GITHUB_TOKEN | docker login ghcr.io -u {username} --password-stdin
docker pull ghcr.io/owner/repo/backend:latest
docker inspect ghcr.io/owner/repo/backend:latest | jq '.[] | .Id'
```

#### Test 5.3: OCI Labels

**Condition**: Image creation

**Expected Behavior**:
- All OCI labels present
- Correct values
- Labels queryable

**Verification**:
```bash
docker inspect ghcr.io/owner/repo/backend:latest | \
  jq '.[] | .Config.Labels' | grep "org.opencontainers"
```

#### Test 5.4: No Push on PR

**Condition**: PR opened with changes

**Expected Behavior**:
- Images build
- Images NOT pushed to registry
- Only artifacts stored

**Verification**:
```bash
# Check workflow logs - should NOT see push commands
gh run view {pr-run-id} --log | grep -i "push" | grep -v "buildx-cache"
```

### 6. Artifact Generation Tests

#### Test 6.1: Build Report Created

**Condition**: Workflow completion

**Expected Behavior**:
- BUILD_REPORT.md created
- Includes metadata
- Includes image information
- Available as artifact

**Verification**:
```bash
# Download artifacts
gh run download {run-id} -n build-report
cat BUILD_REPORT.md
```

#### Test 6.2: Image Tags Manifest

**Condition**: Workflow completion

**Expected Behavior**:
- IMAGE_TAGS.json created
- Valid JSON format
- Contains all tags
- Structured for parsing

**Verification**:
```bash
gh run download {run-id} -n build-report
cat IMAGE_TAGS.json | jq '.'
```

#### Test 6.3: SBOM Generation

**Condition**: Backend and frontend builds

**Expected Behavior**:
- backend-sbom.txt created
- frontend-sbom.txt created
- Lists dependencies
- Includes build metadata

**Verification**:
```bash
gh run download {run-id} -n backend-build-logs
gh run download {run-id} -n frontend-build-logs
cat backend-sbom.txt
cat frontend-sbom.txt
```

#### Test 6.4: Artifact Retention

**Condition**: Artifacts created

**Expected Behavior**:
- Artifacts retained for specified days
- 90 days for reports
- 30 days for logs
- Downloadable from Actions UI

**Verification**:
```bash
# Check artifact dates
gh run download {old-run-id} -n build-report

# Should fail if older than retention policy
```

### 7. GitHub Step Summary Tests

#### Test 7.1: Summary Created

**Condition**: Workflow completion

**Expected Behavior**:
- Summary appears in Actions UI
- Includes build status
- Shows key metrics
- Contains artifact links

**Verification**:
```bash
# Check Actions UI
# Navigate to workflow run → Summary tab
```

#### Test 7.2: Summary Content

**Condition**: Verify build summary

**Expected Behavior**:
- Status: SUCCESS
- Version displayed
- Commit hash shown
- Image names listed
- Performance metrics included

**Verification**:
```bash
# Visual inspection of Actions UI summary
```

### 8. Performance Tests

#### Test 8.1: Backend Build Time

**Condition**: Backend Docker build

**Expected Behavior**:
- With cache: < 3 minutes
- Without cache: < 5 minutes
- Measured from start to push

**Verification**:
```bash
# Check workflow logs for timing
gh run view {run-id} --log | grep -E "Build Backend|completed|duration"
```

#### Test 8.2: Frontend Build Time

**Condition**: Frontend Docker build

**Expected Behavior**:
- With cache: < 3 minutes
- Without cache: < 5 minutes
- Measured from start to push

**Verification**:
```bash
# Check workflow logs
gh run view {run-id} --log | grep -E "Build Frontend|completed|duration"
```

#### Test 8.3: Parallel Execution

**Condition**: Backend and frontend builds

**Expected Behavior**:
- Both jobs run simultaneously
- Not sequentially
- Total time < 10 minutes

**Verification**:
```bash
# Check job timeline in Actions UI
# Or from API:
gh run view {run-id} --json jobs | jq '.jobs[] | {name, startedAt, completedAt}'
```

#### Test 8.4: Cache Hit Rate

**Condition**: Repeated builds on same branch

**Expected Behavior**:
- Cache hits on second run
- Faster build times
- Significant time savings

**Verification**:
```bash
# Run same branch twice
git push origin main
# Wait for first build
git commit --allow-empty -m "test"
git push origin main
# Check logs for cache hits
```

### 9. Security Scanning Tests

#### Test 9.1: Trivy Scan Runs

**Condition**: Push to main or release

**Expected Behavior**:
- Trivy scans backend image
- Trivy scans frontend image
- Results captured in SARIF format

**Verification**:
```bash
# Check scan artifacts
gh run download {run-id} -n security-scan-reports
ls -la *-trivy-results.sarif
```

#### Test 9.2: Security Results Uploaded

**Condition**: Scan completion

**Expected Behavior**:
- SARIF uploaded to GitHub Security
- Appears in Security tab
- Vulnerabilities listed (if any)

**Verification**:
```bash
# Check GitHub Security
gh api repos/{owner}/{repo}/security-and-analysis

# View vulnerability alerts
gh api repos/{owner}/{repo}/security-advisories
```

#### Test 9.3: Image Security

**Condition**: Image creation

**Expected Behavior**:
- No critical vulnerabilities
- No high-severity CVEs in base images
- Security patch applied regularly

**Verification**:
```bash
# Check Trivy results
cat backend-trivy-results.sarif | jq '.runs[].results[].level' | sort | uniq -c
```

### 10. Integration Tests

#### Test 10.1: PR Comment Creation

**Condition**: PR opened with changes

**Expected Behavior**:
- Comment created on PR
- Shows build status
- Lists image tags
- Provides artifact links

**Verification**:
```bash
# Check PR comments
gh pr view {pr-number} --json comments | jq '.comments[].body'
```

#### Test 10.2: Docker Compose Integration

**Condition**: Built images used in docker-compose

**Expected Behavior**:
- Images pull successfully
- Services start correctly
- All containers healthy

**Verification**:
```bash
# Use built images in docker-compose
export BACKEND_IMAGE=ghcr.io/owner/repo/backend:{sha}
export FRONTEND_IMAGE=ghcr.io/owner/repo/frontend:{sha}
docker-compose up -d
sleep 30
docker-compose ps
```

#### Test 10.3: Kubernetes Deployment

**Condition**: Images deployed to Kubernetes

**Expected Behavior**:
- Images pull in K8s cluster
- Pods start successfully
- Health checks pass
- Services accessible

**Verification**:
```bash
kubectl create deployment backend \
  --image=ghcr.io/owner/repo/backend:{sha}
kubectl rollout status deployment/backend
kubectl get pods
```

## Test Execution Matrix

### Manual Testing Checklist

- [ ] Test 1.1: Push to main
- [ ] Test 1.2: Push to develop
- [ ] Test 1.3: Create release tag
- [ ] Test 1.4: Open PR
- [ ] Test 1.5: Manual trigger
- [ ] Test 2.x: Metadata tests
- [ ] Test 3.x: Backend tests
- [ ] Test 4.x: Frontend tests
- [ ] Test 5.x: Registry tests
- [ ] Test 6.x: Artifact tests
- [ ] Test 7.x: Summary tests
- [ ] Test 8.x: Performance tests
- [ ] Test 9.x: Security tests
- [ ] Test 10.x: Integration tests

### Automated Testing

All tests are integrated into the workflow and execute automatically.

## Test Results

### Expected Outcomes

| Component | Status | Evidence |
|-----------|--------|----------|
| Workflow triggers | PASS | Logs in Actions |
| Build metadata | PASS | IMAGE_TAGS.json |
| Backend build | PASS | Image in GHCR |
| Frontend build | PASS | Image in GHCR |
| Image registry | PASS | Pull successful |
| Artifacts | PASS | Downloaded from UI |
| Summary | PASS | Visible in Actions |
| Performance | PASS | < 10 min total |
| Security | PASS | No critical CVEs |
| Integration | PASS | Containers run |

## Failure Handling

### Build Failure Scenarios

1. **Docker Build Fails**
   - Logs available in Actions
   - Check Dockerfile syntax
   - Verify dependencies installed
   - Review base image compatibility

2. **Registry Push Fails**
   - Check GITHUB_TOKEN secret
   - Verify repository settings
   - Check registry authentication
   - Review rate limiting

3. **Security Scan Fails**
   - Review Trivy results
   - Check for CVEs in dependencies
   - Update vulnerable packages
   - Document accepted risks

4. **Performance Degradation**
   - Clear cache and rebuild
   - Review Docker layers
   - Check for large files
   - Profile build process

## Exit Criteria

### Success Criteria

1. All jobs complete successfully
2. Images pushed to GHCR (on main/release)
3. Build artifacts generated
4. Security scans pass
5. Total build time < 10 minutes
6. No critical vulnerabilities

### Failure Criteria

1. Any job times out
2. Build fails on main branch
3. Images cannot be pushed
4. Critical CVE detected
5. Performance degradation > 20%

---

## Test Execution Schedule

- **Continuous**: Every push and PR
- **Nightly**: Full performance baseline
- **Weekly**: Security scanning deep-dive
- **Manual**: On-demand verification

---

**Last Updated**: 2025-01-15
**Status**: Ready for Testing
**Version**: 1.0.0
