# Security Policy

## Reporting Security Vulnerabilities

If you discover a security vulnerability in THE_BOT platform, please email security@thebot.platform with:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

Please do **NOT** create a public GitHub issue for security vulnerabilities.

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | YES       |
| < 1.0   | NO        |

## Security Scanning

The project includes automated security scanning via GitHub Actions:

### Dependency Scanning
- **Backend**: Safety, pip-audit
- **Frontend**: npm audit, Dependency Review

### Static Application Security Testing (SAST)
- **Backend**: Bandit, Semgrep
- **Frontend**: ESLint, Semgrep

### Secret Detection
- **gitleaks**: Detects hardcoded secrets
- **detect-secrets**: Baseline for known secrets

### Schedule
- Automatic on every push to `main` and `develop`
- Automatic on pull requests
- Weekly scheduled scan every Monday at 00:00 UTC

## Security Best Practices

### Authentication
1. Always use strong passwords (12+ characters, mixed case, numbers, symbols)
2. Enable two-factor authentication (2FA) when available
3. Use secure tokens with appropriate expiration times
4. Rotate API keys regularly

### Data Protection
1. Use HTTPS/TLS for all communications
2. Encrypt sensitive data at rest
3. Implement proper access controls
4. Follow principle of least privilege

### Code Security
1. Avoid hardcoding secrets in code
2. Use environment variables for configuration
3. Validate all user inputs
4. Use parameterized queries to prevent SQL injection
5. Implement CSRF protection
6. Use secure serialization methods

### Dependencies
1. Keep dependencies up to date
2. Review security advisories for dependencies
3. Use lock files (package-lock.json, requirements.txt)
4. Test updates in development before production

## Security Headers

The application implements the following security headers:

```
Content-Security-Policy: default-src 'self'
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Referrer-Policy: strict-origin-when-cross-origin
```

## Vulnerability Scoring

Security vulnerabilities are scored using CVSS 3.1:

- **CRITICAL** (9.0-10.0): Requires immediate action
- **HIGH** (7.0-8.9): Should be fixed in next release
- **MEDIUM** (4.0-6.9): Should be addressed soon
- **LOW** (0.1-3.9): Can be addressed in regular updates

## Vulnerability Management Process

1. **Identify**: Scans detect vulnerabilities automatically
2. **Verify**: Confirm the vulnerability and assess impact
3. **Fix**: Create a fix or apply a patch
4. **Test**: Test the fix thoroughly
5. **Release**: Include fix in next release
6. **Document**: Update CHANGELOG and security documentation

## Remediation

### For Dependencies

#### Python (Backend)
```bash
# Check for vulnerabilities
pip-audit --requirements requirements.txt

# Update packages
pip install --upgrade [package-name]

# Update all
pip install --upgrade -r requirements.txt
```

#### Node.js (Frontend)
```bash
# Check for vulnerabilities
npm audit

# Fix automatically
npm audit fix

# Update packages
npm update [package-name]
```

### For Code Issues

1. Review the SAST findings in the workflow artifacts
2. Fix the security issue in the code
3. Run local security scans to verify
4. Submit a pull request with the fix

## Environment Security

### Required Environment Variables
- `SECRET_KEY`: Django secret key (min 50 chars, random)
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `DATABASE_URL`: Database connection string
- `YOOKASSA_SHOP_ID`: Payment system shop ID
- `YOOKASSA_SECRET_KEY`: Payment system secret key

### Never Store Secrets
- Do NOT commit `.env` files
- Do NOT commit credentials
- Do NOT commit API keys
- Do NOT commit private keys

### Secret Detection

The pipeline automatically detects hardcoded secrets using gitleaks. If a secret is found:

1. Remove the secret from the code
2. Revoke the exposed secret
3. Generate a new secret
4. Update environment variables
5. Force push the fix (if necessary)

## Security Improvements

### Recent Improvements
- Dual authentication (token + session-based)
- CSRF protection with token rotation
- Rate limiting (5 login attempts/min)
- Brute force protection (lock after 10 attempts)
- Password policy enforcement
- Security headers implementation
- File upload validation
- SQL injection prevention

### Planned Improvements
- WAF (Web Application Firewall) integration
- DDoS protection
- Advanced threat detection
- Regular security audits
- Bug bounty program

## Third-Party Security Tools

The project uses:
- [GitHub Advanced Security](https://github.com/features/security): Code scanning
- [Semgrep](https://semgrep.dev/): SAST scanning
- [Safety](https://pyup.io/): Python dependency scanning
- [npm audit](https://docs.npmjs.com/cli/audit): Node.js vulnerability scanning
- [gitleaks](https://github.com/gitleaks/gitleaks): Secret detection
- [detect-secrets](https://github.com/Yelp/detect-secrets): Secret baseline management

## Security Contact

- Email: security@thebot.platform
- GPG Key: [Available on request]

## Acknowledgments

We thank all security researchers who responsibly disclose vulnerabilities to us.

## License

This security policy is licensed under CC0 1.0 Universal.
