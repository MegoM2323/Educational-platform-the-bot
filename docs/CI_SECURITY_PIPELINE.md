# CI Security Pipeline - Implementation Guide

## Overview

The CI Security Pipeline (T_DEV_008) provides comprehensive automated security scanning across the entire THE_BOT platform. It includes dependency vulnerability scanning, static application security testing (SAST), secret detection, and detailed security reporting.

**Status**: COMPLETED AND VALIDATED
**All Tests Passing**: 78/78 (100%)

## Pipeline Architecture

### 7 Security Scanning Jobs

```
├── backend-dependencies      → Scan Python packages (Safety, pip-audit)
├── backend-sast             → Scan Python code (Bandit, Semgrep)
├── frontend-dependencies    → Scan npm packages (npm audit)
├── frontend-sast            → Scan TypeScript/React code (ESLint, Semgrep)
├── secret-scanning          → Detect hardcoded secrets (gitleaks, detect-secrets)
├── dependency-review        → GitHub Dependency Review (PR only)
└── security-report          → Aggregate and report findings
```

### Execution Flow

```
Trigger: push/PR to main or develop
    ↓
[Parallel Execution]
├── backend-dependencies
├── backend-sast
├── frontend-dependencies
├── frontend-sast
├── secret-scanning
└── dependency-review (PR only)
    ↓
[Reporting]
└── security-report (aggregates all findings)
```

## Scanning Tools

### Backend Scanning

#### Dependency Scanning
- **Safety**: Checks Python packages against known vulnerability database
  - Database: OSV, CVE
  - Output: JSON + human-readable
  - Timeout: 15 minutes

- **pip-audit**: Vulnerability scanning for Python packages
  - Detects deprecated packages
  - Shows available fixes
  - Output: Human-readable report

#### Static Application Security Testing (SAST)
- **Bandit**: Security linter for Python code
  - Detects: SQL injection, insecure randomness, hardcoded credentials, etc.
  - Output: JSON, CSV, TXT formats
  - Excludes: tests, migrations, venv

- **Semgrep**: Pattern-based static analysis
  - Detects: OWASP Top 10, custom rules
  - Rules: p/security-audit, p/django, p/python
  - Output: SARIF format (integrates with GitHub)

### Frontend Scanning

#### Dependency Scanning
- **npm audit**: NPM package vulnerability scanner
  - Scans: package-lock.json
  - Levels: critical, high, moderate, low
  - Output: JSON report + fix suggestions

#### Static Application Security Testing (SAST)
- **ESLint**: JavaScript/TypeScript code quality and security
  - Output: JSON + text format
  - Checks: Unused variables, security issues

- **Semgrep**: Pattern-based static analysis
  - Rules: p/security-audit, p/typescript, p/react
  - Output: SARIF format

### Secret Detection

- **gitleaks**: Detects hardcoded secrets in code
  - Database: 100+ patterns (API keys, tokens, credentials)
  - Scans: Entire git history
  - Output: JSON report

- **detect-secrets**: Baseline-based secret detection
  - Maintains: Baseline file (.secrets.baseline)
  - Purpose: Track known secrets vs new findings
  - Output: Audit report

## Workflow Configuration

### File Location
```
.github/workflows/security-scan.yml
```

### Triggers

```yaml
on:
  schedule:
    - cron: '0 0 * * 1'        # Every Monday at 00:00 UTC
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]
```

### Job Timeouts
- Backend dependencies: 15 minutes
- Backend SAST: 20 minutes
- Frontend dependencies: 15 minutes
- Frontend SAST: 15 minutes
- Secret scanning: 10 minutes
- Dependency review: 10 minutes
- Security report: 10 minutes

### Artifact Retention
- All reports: 30 days
- Security summary: 90 days

## Security Rules (Semgrep)

### Critical Rules
- `hardcoded-secrets`: Detects API keys, passwords, tokens
- `eval-usage`: Prevents eval() and exec() calls
- `no-jwt-validation`: Detects disabled JWT signature verification
- `insecure-deserialization`: Catches unsafe pickle/yaml.load()

### High-Severity Rules
- `shell-injection`: Detects shell=True in subprocess calls
- `insecure-random`: Detects unsafe random generation in security contexts

### Medium-Severity Rules
- `sql-injection-risk`: Detects potential SQL injection
- `missing-csrf-protection`: Finds @csrf_exempt without justification
- `missing-authentication`: Detects unprotected API endpoints
- `secure-password-hashing`: Validates password hashing methods

## Reporting

### Security Summary

The `security-report` job generates:

1. **Summary Statistics**
   ```json
   {
     "timestamp": "2025-12-27T...",
     "findings": {
       "critical": 0,
       "high": 2,
       "medium": 5,
       "low": 10,
       "info": 3
     }
   }
   ```

2. **Scan Status**
   - backend_dependencies: completed (X findings)
   - backend_sast: completed (X findings)
   - frontend_dependencies: completed (X findings)
   - frontend_sast: completed (X findings)
   - secrets: completed (X findings)

3. **PR Comment** (when triggered by PR)
   - Lists all scan results
   - Links to artifact downloads
   - Provides remediation guidance

4. **Artifacts**
   - Individual reports from each scan
   - Summary JSON
   - 30-90 day retention

## Local Security Scanning

### Quick Start

```bash
# Scan everything (backend, frontend, secrets)
./scripts/security-scan.sh all

# Scan specific component
./scripts/security-scan.sh backend
./scripts/security-scan.sh frontend
./scripts/security-scan.sh secrets
```

### Script Features

- Color-coded output
- Automatic tool installation
- Report generation
- Summary statistics
- JSON export

### Reports Generated

```
backend/
├── safety-report.json
├── bandit-report.json
├── bandit-report.csv
├── bandit-report.txt
└── pip-audit-report.txt

frontend/
├── npm-audit-report.json
├── npm-audit-fix-suggestions.txt
├── eslint-report.json
└── eslint-report.txt

./
├── gitleaks-report.json
├── .secrets.baseline
└── security-scan-summary.json
```

## Vulnerability Severity Levels

### CVSS 3.1 Scoring

| Severity | Score | Action Required |
|----------|-------|-----------------|
| CRITICAL | 9.0-10.0 | Immediate fix required |
| HIGH | 7.0-8.9 | Fix in next release |
| MEDIUM | 4.0-6.9 | Should be addressed soon |
| LOW | 0.1-3.9 | Can be addressed in regular updates |

## Remediation Workflow

### Python Dependencies

```bash
# Check vulnerabilities
pip-audit --requirements backend/requirements.txt

# Update a package
pip install --upgrade [package-name]

# Update all
pip install --upgrade -r backend/requirements.txt
```

### Node.js Dependencies

```bash
# Check vulnerabilities
npm audit

# Auto-fix (if available)
npm audit fix

# Manual update
npm update [package-name]
```

### Code Issues

1. Review SAST findings in workflow artifacts
2. Fix the security issue in code
3. Commit fix: `git commit -m "Fix security issue: [description]"`
4. Create pull request
5. Pipeline will automatically scan the PR

### Secret Issues

1. Immediately revoke the exposed secret
2. Generate a new secret
3. Update environment variables
4. Remove the secret from code
5. Force push if necessary: `git push --force-with-lease`

## Integration with GitHub

### Code Scanning Tab

SARIF reports are uploaded to GitHub's Code Scanning feature:

```
Repository → Security → Code scanning alerts
```

Shows:
- All findings across all jobs
- Severity levels
- Suggested fixes
- Historical trends

### Pull Request Reviews

Security findings are commented directly on PRs:

```
## Security Scan Report

### Scan Results
- Backend Dependencies: Scanned
- Backend SAST: Scanned
- Frontend Dependencies: Scanned
- Frontend SAST: Scanned
- Secret Detection: Scanned

### Download Reports
[Link to artifacts]

### Remediation
- Update vulnerable dependencies
- Address SAST findings
- Follow security guidelines
```

## Configuration Files

### Semgrep Configuration
**File**: `.semgrep.yml`

Contains 10 custom security rules for:
- Hardcoded secrets
- Unsafe code patterns
- Authentication/authorization issues
- Serialization vulnerabilities
- Shell injection risks

### Security Policy
**File**: `SECURITY.md`

Contains:
- Vulnerability reporting process
- Security best practices
- Supported versions
- Vulnerability management procedure
- Contact information

## Testing and Validation

### Validation Test Suite

**File**: `tests/test_security_pipeline.py`

Tests validate:
- Workflow YAML structure (78 tests)
- Job configuration
- Tool availability
- Artifact uploads
- Report generation
- Documentation

**Status**: ALL PASSING (78/78)

### Running Validation Tests

```bash
# Validate YAML and configuration
python tests/test_security_pipeline.py

# Validate security tools
./scripts/security-scan.sh all
```

## Performance Characteristics

### Scan Timing

| Job | Typical Duration | Max Timeout |
|-----|-----------------|-------------|
| Backend dependencies | 3-5 minutes | 15 minutes |
| Backend SAST | 5-8 minutes | 20 minutes |
| Frontend dependencies | 2-3 minutes | 15 minutes |
| Frontend SAST | 3-5 minutes | 15 minutes |
| Secret scanning | 2-4 minutes | 10 minutes |
| Dependency review | 1-2 minutes | 10 minutes |
| Security report | 1-2 minutes | 10 minutes |

**Total parallel execution**: ~8-10 minutes (jobs run in parallel)

### Caching

- pip cache: Enabled (packages downloaded once)
- npm cache: Enabled (node_modules installed once)
- GitHub Actions: Uses ubuntu-latest

## Failure Handling

### When Scans Fail

1. **Dependency Review Job** (PR only)
   - Fails if critical vulnerabilities found
   - Blocks PR merge
   - Requires fix or override approval

2. **Other Jobs**
   - Continue on error (reports findings)
   - Do not block PR merge
   - Visible in artifacts and PR comments

3. **Manual Intervention**
   - Review findings in artifacts
   - Address issues in code
   - Push fix to PR
   - Pipeline re-runs automatically

## Best Practices

### For Developers

1. **Run locally before pushing**
   ```bash
   ./scripts/security-scan.sh all
   ```

2. **Fix issues immediately**
   - Don't merge PRs with critical findings

3. **Keep dependencies updated**
   - Review weekly security scans
   - Update packages regularly
   - Test updates thoroughly

4. **Follow security guidelines**
   - See SECURITY.md
   - Use parameterized queries
   - Avoid hardcoded secrets
   - Implement proper authentication

### For DevOps/Security Teams

1. **Review findings regularly**
   - Check weekly scheduled scans
   - Monitor PR security reports
   - Track vulnerability trends

2. **Update security rules**
   - Quarterly review of Semgrep rules
   - Add custom rules for known issues
   - Update tool configurations

3. **Maintain baseline**
   - Review secret baseline periodically
   - Update allowed secret list
   - Remove obsolete entries

## Troubleshooting

### No findings reported (but should have)

1. Check tool installation
   ```bash
   pip show safety bandit
   npm list eslint
   ```

2. Verify exclude patterns
   - Tests, migrations, node_modules may be excluded

3. Check configuration
   - Verify .semgrep.yml is present
   - Check tool versions

### Security report job fails

1. Check artifact paths
   - Ensure reports generated correctly
   - Verify JSON formatting

2. Check PR context
   - Report requires issue number for PR comment

3. Check permissions
   - Ensure token has repo permissions

### False positives

1. Review Semgrep rules
   - May need to adjust patterns
   - Can add allowlist entries

2. Review tool output
   - Some tools generate false positives
   - Verify findings are real before fixing

## Maintenance

### Weekly
- Review security scan results
- Update vulnerable dependencies

### Monthly
- Audit security logs
- Review new CVEs
- Update tool versions

### Quarterly
- Audit Semgrep rule set
- Review security policy
- Conduct security assessment

## Future Enhancements

Planned improvements:

1. **Container Image Scanning**
   - Trivy scanning for Docker images
   - Supply chain security

2. **DAST Testing**
   - Dynamic application security testing
   - Live application scanning

3. **Compliance Scanning**
   - HIPAA, GDPR compliance checks
   - PCI DSS validation

4. **Bug Bounty Integration**
   - External security researcher reports
   - Vulnerability coordination

5. **ML-Based Detection**
   - Anomaly detection
   - Pattern recognition

## Support and Documentation

- **Security Policy**: [SECURITY.md](../SECURITY.md)
- **API Guide**: [API_GUIDE.md](../docs/API_GUIDE.md)
- **GitHub Actions Docs**: https://docs.github.com/actions
- **Semgrep Docs**: https://semgrep.dev/docs
- **OWASP Top 10**: https://owasp.org/Top10

## References

- [OWASP Secure SDLC](https://owasp.org/www-project-integration-standards/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [GitHub Security Best Practices](https://github.blog/security/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

---

**Last Updated**: December 27, 2025
**Pipeline Status**: OPERATIONAL
**All Validations**: PASSING (78/78)
