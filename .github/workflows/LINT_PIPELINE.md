# CI Pipeline Lint Workflow Documentation

## Overview

The **CI Pipeline Lint** workflow provides comprehensive code quality checking across the entire THE_BOT platform, including:

- **Python Code**: Flake8, Black, isort, pylint, mypy
- **JavaScript/TypeScript**: ESLint, TypeScript, Prettier
- **Configuration Files**: YAML, JSON, Markdown
- **Dependency Security**: pip-audit, npm audit

## Workflow Triggers

The workflow runs automatically on:

- **Push** to `main`, `develop`, or `feature/**` branches
- **Pull Requests** to `main` or `develop` branches
- **Manual trigger** via GitHub Actions UI (`workflow_dispatch`)

## Jobs

### 1. Python Code Quality (`python-lint`)

**Purpose**: Validate Python code style, formatting, and type hints.

**Linting Tools**:

- **Flake8**: Error and style checking
  - Critical errors: E9, F63, F7, F82
  - Style violations: E (error), W (warning), F (pyflakes), C (complexity), N (naming)
  - Max line length: 127 characters
  - Max complexity: 10

- **Black**: Code formatting
  - Line length: 127 characters
  - Enforces consistent Python style

- **isort**: Import sorting
  - Profiles: Black-compatible
  - Groups and sorts imports automatically

- **mypy**: Static type checking
  - Python version: 3.11
  - Ignores missing imports
  - Shows error codes and context

- **pylint**: Code analysis
  - Complex code detection
  - Unused variable detection
  - Code smell identification

**Configuration Files**:
- `.flake8` - Flake8 settings
- `.pylintrc` - Pylint settings
- `mypy.ini` - Mypy settings

**Duration**: ~3-5 minutes

### 2. JavaScript/TypeScript Code Quality (`javascript-lint`)

**Purpose**: Validate JavaScript/TypeScript code quality and formatting.

**Linting Tools**:

- **ESLint**: JavaScript/TypeScript linting
  - Configuration: `frontend/eslint.config.js`
  - Detects errors and warnings
  - React hooks validation
  - React refresh optimization

- **TypeScript**: Type checking
  - Command: `npm run type-check`
  - Strict type validation
  - No emit (checking only)

- **Prettier**: Code formatting
  - Line width: 100 characters
  - Single quotes for JS/TS
  - Trailing commas (ES5)
  - Automatic formatting

**Configuration Files**:
- `frontend/eslint.config.js` - ESLint settings
- `frontend/.prettierrc.json` - Prettier settings

**Duration**: ~2-4 minutes

### 3. YAML Validation (`yaml-lint`)

**Purpose**: Validate YAML syntax and structure.

**Tool**: yamllint

**Scans**:
- `.github/` - GitHub Actions workflows
- `backend/` - Python configuration files
- `frontend/` - Frontend configuration files

**Rules**:
- Line length: max 120 characters (warning)
- Indentation: 2 spaces
- Comments: 1 space from content
- Truthy values: yes, no, true, false

**Duration**: ~1 minute

### 4. JSON Validation (`json-lint`)

**Purpose**: Validate JSON file syntax.

**Tool**: jq (JSON processor)

**Scans**:
- All `.json` files
- Excludes: `node_modules/`, `.venv/`, `.git/`

**Validation**:
- Proper JSON syntax
- Valid UTF-8 encoding
- No trailing commas

**Duration**: ~1 minute

### 5. Markdown Linting (`markdown-lint`)

**Purpose**: Validate Markdown formatting and style.

**Tool**: markdownlint

**Configuration**: `.markdownlint.json`

**Rules Enforced**:
- Heading hierarchy (no skipped levels)
- No duplicate headings
- Proper spacing around lists/headings
- Line length: 120 characters
- Consistent list markers

**Duration**: ~1 minute

### 6. Dependency Security Scanning (`dependency-scan`)

**Purpose**: Identify vulnerable dependencies.

**Tools**:

- **pip-audit**: Python dependency scanning
  - Checks for known vulnerabilities
  - Reports detailed descriptions
  - Severity levels

- **npm audit**: JavaScript dependency scanning
  - Checks for known vulnerabilities
  - Audit level: moderate and above
  - Suggests fixes

**Duration**: ~3-5 minutes

### 7. Lint Summary & Report (`lint-summary`)

**Purpose**: Aggregate results and report status.

**Dependencies**: All other jobs

**Outputs**:
- Generates lint summary report
- Creates PR comment with results (on PR events)
- Provides artifact with full reports
- Exits with failure if critical jobs failed

**Duration**: ~1 minute

## Configuration Files

### Python Linting

#### `.flake8`
```ini
[flake8]
max-line-length = 127
max-complexity = 10
exclude = migrations,__pycache__,.venv,venv
ignore = E203,E501,W503,W504
```

#### `.pylintrc`
```ini
[MASTER]
ignore = migrations,__pycache__,.venv,venv

[FORMAT]
max-line-length = 127

[DESIGN]
max-args = 10
max-attributes = 10
```

#### `mypy.ini`
```ini
[mypy]
python_version = 3.11
ignore_missing_imports = True
warn_unused_ignores = True
```

### JavaScript Linting

#### `frontend/.prettierrc.json`
```json
{
  "semi": true,
  "singleQuote": true,
  "printWidth": 100,
  "tabWidth": 2,
  "trailingComma": "es5"
}
```

#### `frontend/eslint.config.js`
Already configured with TypeScript and React support.

### Other Configuration

#### `.markdownlint.json`
Markdown style enforcement with rules for:
- Line length (120 chars)
- Heading hierarchy
- List formatting
- Emphasis consistency

## Performance Optimizations

### Caching

- **pip cache**: Caches Python packages by requirements hash
- **npm cache**: Caches node_modules by package-lock hash
- Cache key versioning: `CACHE_VERSION` env variable for cache busting

### Parallel Execution

All jobs run in parallel except:
- `lint-summary` waits for all other jobs (dependency job)

**Estimated Total Time**: 5-10 minutes

## Reporting & Artifacts

### Generated Reports

The workflow generates the following artifacts:

**Python Reports**:
- `python-lint-reports/flake8-critical.json` - Critical errors
- `python-lint-reports/flake8-report.txt` - Style violations
- `python-lint-reports/black-report.txt` - Formatting issues
- `python-lint-reports/isort-report.txt` - Import order issues
- `python-lint-reports/mypy-report.txt` - Type checking issues
- `python-lint-reports/pylint-report.txt` - Code analysis

**JavaScript Reports**:
- `javascript-lint-reports/eslint-report.json` - JSON format
- `javascript-lint-reports/eslint-report.txt` - Human-readable format
- `javascript-lint-reports/typescript-report.txt` - Type checking
- `javascript-lint-reports/prettier-report.txt` - Formatting issues

**Dependency Reports**:
- `dependency-scan-reports/pip-audit-report.txt` - Python vulnerabilities
- `dependency-scan-reports/npm-audit-report.txt` - JavaScript vulnerabilities

**Summary**:
- `lint-summary/lint-summary.md` - Aggregated report

### PR Comments

On pull requests, the workflow automatically comments with:
- Lint summary status
- Job results
- Links to artifact reports

### Artifact Retention

All artifacts are retained for **30 days**.

## Error Codes & Solutions

### Flake8 Errors

| Code | Issue | Solution |
|------|-------|----------|
| E302 | Expected 2 blank lines | Add blank lines between functions |
| E501 | Line too long | Format with Black or split line |
| F401 | Imported but unused | Remove unused import or add to `__all__` |
| W391 | Blank line at EOF | Remove trailing blank line |

### Black Formatting

Use Black to auto-fix:
```bash
black backend/
```

### isort Import Ordering

Use isort to auto-fix:
```bash
isort --profile=black backend/
```

### ESLint/TypeScript Errors

Use ESLint fix:
```bash
cd frontend && npm run lint -- --fix
```

## Local Linting

To run linting locally before pushing:

### Python

```bash
# Install tools
pip install flake8 black isort mypy pylint

# Run all checks
cd backend
flake8 .
black --check .
isort --check-only .
mypy .
pylint **/*.py
```

### JavaScript

```bash
# Install dependencies
cd frontend
npm install

# Run linting
npm run lint
npm run type-check
npx prettier --check "src/**/*.{ts,tsx,js,jsx}"
```

### YAML & JSON

```bash
# Install tools
pip install yamllint
npm install -g jsonlint

# Validate
yamllint .github/
find . -name "*.json" | xargs jq empty
```

## Troubleshooting

### Workflow Failures

1. **Check artifact reports** in GitHub Actions UI
2. **Review PR comment** for summary
3. **Run linting locally** to reproduce issues
4. **Fix issues** using tool-specific fixes

### Common Issues

#### Markdown files won't validate
- Ensure `.markdownlint.json` exists in root
- Check line lengths don't exceed 120 chars
- Verify heading hierarchy

#### Python import errors in mypy
- Add to `mypy.ini` ignore list
- Check `__init__.py` files exist in packages
- Verify type stub packages are installed

#### ESLint errors in node_modules
- Ensure `eslint.config.js` has proper ignores
- Clear npm cache: `npm cache clean --force`
- Reinstall: `rm -rf node_modules && npm install`

## Maintenance

### Updating Linting Tools

1. Update tool versions in workflow file (steps section)
2. Test locally first
3. Update configuration files if needed
4. Create pull request with changes
5. Verify workflow passes

### Adjusting Rules

1. Modify configuration files (`.flake8`, `.pylintrc`, etc.)
2. Update rules in workflow jobs if needed
3. Test with `continue-on-error: true` first
4. Change to `continue-on-error: false` when confident

### Adding New Linters

1. Add new job to workflow
2. Create configuration file if needed
3. Add to `lint-summary` dependencies
4. Document in this file
5. Test in feature branch first

## Related Documentation

- [API_GUIDE.md](../../docs/API_GUIDE.md) - API usage
- [SECURITY.md](../../docs/SECURITY.md) - Security practices
- [DEPLOYMENT.md](../../docs/DEPLOYMENT.md) - Deployment guide

## Questions & Support

For issues with the lint pipeline:
1. Check this documentation
2. Review GitHub Actions logs
3. Check artifact reports
4. Test linting locally
5. Open issue if bug is found

---

Last Updated: December 27, 2025
Workflow Version: 1.0.0
Status: Production Ready
