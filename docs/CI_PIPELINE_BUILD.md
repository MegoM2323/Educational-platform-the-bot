# CI Pipeline Build Documentation

## Overview

The CI Pipeline Build (`.github/workflows/build.yml`) is a comprehensive GitHub Actions workflow that automates the building, testing, and deployment of Docker images for the THE_BOT platform.

## Workflow Phases

### Phase 1: Setup & Prepare Build Metadata

**Job**: `setup`

Generates build metadata used throughout the pipeline:

- **Build Date**: ISO 8601 timestamp
- **Git SHA**: Full commit hash
- **Git Ref**: Branch or tag name
- **Version**: Semantic version or git describe
- **Image Metadata**: OCI-compliant labels

#### Outputs

```json
{
  "backend_image": "ghcr.io/owner/repo/backend",
  "frontend_image": "ghcr.io/owner/repo/frontend",
  "backend_tags": ["latest", "sha", "branch"],
  "frontend_tags": ["latest", "sha", "branch"],
  "build_date": "2025-01-15T10:30:45Z",
  "git_sha": "abc123def456",
  "git_ref": "main",
  "version": "v1.0.0",
  "is_release": true
}
```

### Phase 2: Build Backend Docker Image

**Job**: `build-backend`

Builds the Django backend Docker image.

#### Features

- Multi-platform support (linux/amd64, linux/arm64)
- Docker layer caching
- BuildKit acceleration
- OCI Image spec compliance

#### Build Arguments

```bash
BUILD_DATE=2025-01-15T10:30:45Z
VCS_REF=abc123def456
VERSION=v1.0.0
```

#### Docker Buildx Configuration

- Platforms: linux/amd64, linux/arm64
- Cache strategy: Local file system
- Progress: Plain text
- BuildKit: Latest

#### Caching Strategy

```
Key: buildx-backend-{branch}-{sha}
Fallback: buildx-backend-{branch}-, buildx-backend-main-
```

This enables:
- Branch-specific caches
- Fallback to main branch cache
- Efficient layer reuse

#### Outputs

- Image digest (SHA256)
- Tagged images in GHCR
- SBOM (Software Bill of Materials)

### Phase 3: Build Frontend Docker Image

**Job**: `build-frontend`

Builds the React frontend Docker image.

#### Features

- Multi-platform support (linux/amd64, linux/arm64)
- NPM dependency caching
- Docker layer caching
- Build optimization with Vite

#### Build Arguments

```bash
BUILD_DATE=2025-01-15T10:30:45Z
VCS_REF=abc123def456
VERSION=v1.0.0
VITE_DJANGO_API_URL=http://localhost:8000
VITE_WEBSOCKET_URL=ws://localhost:8000
```

#### Caching Strategy

```
npm cache:
  Key: npm-{lock-hash}
  Fallback: npm-

Docker layers:
  Key: buildx-frontend-{branch}-{sha}
  Fallback: buildx-frontend-{branch}-, buildx-frontend-main-
```

#### Outputs

- Image digest (SHA256)
- Tagged images in GHCR
- SBOM (Software Bill of Materials)

### Phase 4: Verify Build & Generate Artifacts

**Job**: `verify-build`

Creates comprehensive build reports and documentation.

#### Generated Artifacts

1. **BUILD_REPORT.md**
   - Build metadata
   - Image information
   - Build duration estimates
   - Caching details

2. **IMAGE_TAGS.json**
   - Structured image tags
   - Platform information
   - Registry location

3. **SBOM Files**
   - Backend software bill of materials
   - Frontend software bill of materials
   - Dependency documentation

#### GitHub Step Summary

Creates a markdown summary in the Actions UI showing:
- Build status
- Version information
- Image tags
- Artifact locations
- Performance metrics

### Phase 5: Security Scanning (Optional)

**Job**: `scan-images`

Runs vulnerability scanning on built images.

#### Tools

- **Trivy**: Container image vulnerability scanner
- **SARIF Upload**: GitHub CodeQL integration

#### Scanning Details

- Images scanned: Backend and Frontend
- Output format: SARIF (static analysis results)
- Results uploaded to: GitHub Security
- Reports stored as: Artifacts (90-day retention)

#### Conditions

- Triggered on: push to main/develop, releases
- Skipped on: pull requests (by default)

### Phase 6: Notify Results

**Job**: `notify`

Sends build completion notifications.

#### Features

- GitHub PR comments with build status
- Build artifact links
- Performance metrics
- Image tag information

#### PR Comment

Includes:
- Backend image reference
- Frontend image reference
- Build metadata
- Artifact links
- Status indicators

## Triggering the Workflow

### Automatic Triggers

```yaml
on:
  push:
    branches:
      - main
      - develop
    tags:
      - 'v*'
  pull_request:
    branches:
      - main
      - develop
```

### Manual Trigger

```bash
# Via GitHub CLI
gh workflow run build.yml \
  -f push_to_registry=true

# Via GitHub Web UI
# Actions → CI Pipeline Build → Run Workflow
```

## Build Tagging Strategy

### Tag Patterns

| Trigger | Tags |
|---------|------|
| Push to main | `latest`, `{sha}`, `main` |
| Push to develop | `develop`, `{sha}` |
| Release tag (v1.0.0) | `latest`, `{sha}`, `v1.0.0` |
| PR | `{sha}` (no push) |

### Example Tags

```
ghcr.io/owner/repo/backend:latest
ghcr.io/owner/repo/backend:abc123def456
ghcr.io/owner/repo/backend:main
ghcr.io/owner/repo/backend:v1.0.0

ghcr.io/owner/repo/frontend:latest
ghcr.io/owner/repo/frontend:abc123def456
ghcr.io/owner/repo/frontend:develop
```

## Image Registry

### Configuration

- **Registry**: GitHub Container Registry (GHCR)
- **Authentication**: Automatic via `GITHUB_TOKEN`
- **URL Format**: `ghcr.io/{owner}/{repo}/{image}`

### Push Conditions

Images are pushed to GHCR when:
- NOT on pull request
- AND (on main branch OR tagged release)

Pull requests:
- Build images locally
- Do NOT push to registry
- Verify build artifacts only

## Performance Optimization

### Build Time Targets

| Component | Target | Status |
|-----------|--------|--------|
| Backend build | < 5 min | ✓ (with cache) |
| Frontend build | < 5 min | ✓ (with cache) |
| Total pipeline | < 10 min | ✓ (parallel) |

### Optimization Techniques

1. **Multi-stage Builds**
   - Backend: builder → runtime (slim image)
   - Frontend: builder → nginx (minimal runtime)

2. **Layer Caching**
   - Docker BuildKit for incremental builds
   - Dependencies cached before source code
   - Branch-specific caches

3. **Parallel Execution**
   - Backend and frontend builds in parallel
   - No dependencies between builds
   - Independent caching strategies

4. **Dependency Caching**
   - NPM cache: `node_modules`, npm cache
   - Python: Wheel caching in Docker layers
   - Pip cache: `~/.cache/pip`

## Artifact Retention

| Artifact | Retention | Purpose |
|----------|-----------|---------|
| Build Report | 90 days | Documentation |
| Image Tags | 90 days | Reference |
| SBOM Files | 30 days | Security audit |
| Build Logs | 30 days | Troubleshooting |
| Security Scans | 90 days | Compliance |

## Secrets & Environment Variables

### Required Secrets

None required for basic operation.

### Optional Secrets

```bash
# Frontend build environment
VITE_DJANGO_API_URL=http://api.example.com
VITE_WEBSOCKET_URL=ws://api.example.com
```

### Default Environment Variables

```bash
REGISTRY=ghcr.io
IMAGE_NAME=${{ github.repository }}
DOCKER_BUILDKIT=1
BUILDKIT_PROGRESS=plain
```

## Docker Image Specifications

### Backend Image

```
Base Image: python:3.13-alpine3.21
Size: ~350 MB (estimated)
Runtime: gunicorn + uvicorn workers
Health Check: /api/system/health/
Port: 8000
User: appuser (UID 1001)
```

### Frontend Image

```
Base Image: nginx:1.27-alpine
Size: ~20 MB (estimated)
Runtime: nginx
Health Check: GET /
Port: 3000
User: www-data (UID 1001)
```

### OCI Labels

Both images include:

```
org.opencontainers.image.created
org.opencontainers.image.revision
org.opencontainers.image.version
org.opencontainers.image.source
org.opencontainers.image.title
org.opencontainers.image.description
```

## Debugging & Troubleshooting

### View Build Logs

```bash
# Via GitHub CLI
gh workflow view build.yml
gh workflow run build.yml --list

# Via GitHub Web UI
# Actions → CI Pipeline Build → Select run → View logs
```

### Common Issues

#### Build Timeout

**Symptom**: Job exceeds 30-minute timeout

**Solution**:
- Check for hung processes
- Review Docker layer caching
- Increase timeout in workflow file

#### Registry Authentication

**Symptom**: `Error: login required`

**Solution**:
- Verify GITHUB_TOKEN secret is available
- Check repository settings → Actions → General → Workflow permissions
- Enable "Read and write permissions"

#### Cache Not Working

**Symptom**: Same dependencies rebuilt every run

**Solution**:
- Verify cache action version (use v4)
- Check cache key matches
- Review cache hit/miss in workflow logs
- Consider increasing cache size limits

#### Image Size Too Large

**Symptom**: Image push fails or takes too long

**Solution**:
- Review multi-stage build process
- Remove unnecessary dependencies
- Enable Docker buildkit optimizations
- Use alpine base images

### Debug Output

Enable verbose logging:

```yaml
env:
  BUILDKIT_PROGRESS: verbose  # or: plain, tty
```

## Integration Examples

### Using Built Images

#### Pull Image

```bash
docker pull ghcr.io/owner/repo/backend:latest
docker pull ghcr.io/owner/repo/frontend:latest
```

#### Run with Docker Compose

```bash
cat > .env <<EOF
BACKEND_IMAGE=ghcr.io/owner/repo/backend:latest
FRONTEND_IMAGE=ghcr.io/owner/repo/frontend:latest
EOF

docker-compose up -d
```

#### Deploy to Kubernetes

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: thebot
spec:
  containers:
  - name: backend
    image: ghcr.io/owner/repo/backend:latest
    ports:
    - containerPort: 8000
  - name: frontend
    image: ghcr.io/owner/repo/frontend:latest
    ports:
    - containerPort: 3000
```

### Continuous Deployment

Chain with deployment workflow:

```yaml
on:
  workflow_run:
    workflows: ["CI Pipeline Build"]
    branches: [main]
    types:
      - completed

jobs:
  deploy:
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    runs-on: ubuntu-latest
    steps:
      # Deploy using built images
```

## Monitoring & Analytics

### GitHub Actions Metrics

- **Workflow runs**: GitHub Actions → Workflows → build.yml
- **Performance trends**: Graphs show build time over time
- **Resource usage**: CPU, memory, duration

### Build Artifacts

Monitor through:
- GitHub Actions → Artifacts
- GitHub API: `/repos/{owner}/{repo}/actions/artifacts`

### Registry Analytics

GHCR provides:
- Image size over time
- Pull statistics
- Tag analytics

## Security Best Practices

1. **Non-root User**
   - Backend: appuser (UID 1001)
   - Frontend: www-data (UID 1001)

2. **Minimal Base Images**
   - Alpine Linux for smaller surface area
   - Only runtime dependencies in final image

3. **Health Checks**
   - Backend: `/api/system/health/`
   - Frontend: `GET /`
   - Ensures container readiness

4. **Vulnerability Scanning**
   - Trivy scans for CVEs
   - Results in GitHub Security tab
   - Historical tracking

5. **Image Signing** (Optional)
   - Can be added with cosign
   - SLSA framework compatible

## Related Documentation

- [DEPLOYMENT.md](DEPLOYMENT.md) - Production deployment
- [DOCKER_SETUP.md](DOCKER_SETUP.md) - Local Docker setup
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [API_GUIDE.md](API_GUIDE.md) - API usage

## Support & Resources

### Helpful Links

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Buildx Documentation](https://docs.github.com/en/actions/publishing-packages/publishing-docker-images#building-and-pushing-images)
- [OCI Image Spec](https://github.com/opencontainers/image-spec)
- [Trivy Scanner](https://github.com/aquasecurity/trivy)

### Getting Help

1. Check workflow logs in GitHub Actions
2. Review this documentation
3. Check build artifacts for reports
4. Search GitHub Issues
5. Contact DevOps team

---

## Changelog

### Version 1.0.0 (2025-01-15)

- Initial CI Pipeline Build implementation
- Multi-platform image builds (amd64, arm64)
- Comprehensive artifact generation
- Security scanning integration
- Performance optimization

---

**Last Updated**: 2025-01-15
**Status**: Production Ready
**Version**: 1.0.0
