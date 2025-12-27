# Security Headers Configuration

This document explains the security headers configured in `nginx/the-bot.ru.conf` for the THE_BOT Platform frontend.

## Overview

Security headers are HTTP response headers that instruct browsers to implement specific security policies. They protect against common web vulnerabilities including XSS, clickjacking, MIME type sniffing, and more.

## Headers Configuration

### 1. Strict-Transport-Security (HSTS)

```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
```

**Purpose**: Force HTTPS for all connections
- **max-age=31536000**: Cache policy for 1 year (31,536,000 seconds)
- **includeSubDomains**: Apply to all subdomains
- **preload**: Allow inclusion in browser HSTS preload list

**Protection Against**: Man-in-the-middle attacks, protocol downgrade attacks

**Browser Support**: All modern browsers

### 2. Content-Security-Policy (CSP)

```
Content-Security-Policy: default-src 'self';
                        script-src 'self' 'unsafe-inline' 'unsafe-eval';
                        style-src 'self' 'unsafe-inline';
                        img-src 'self' data: https:;
                        font-src 'self' data:;
                        connect-src 'self' wss: ws:;
                        frame-ancestors 'none';
                        base-uri 'self';
                        form-action 'self';
```

**Directives**:
- **default-src 'self'**: Load resources only from same origin by default
- **script-src**: Inline scripts, eval allowed (for React development)
- **style-src**: Inline styles allowed (CSS-in-JS support)
- **img-src**: Images from same origin, data URLs, or HTTPS
- **font-src**: Fonts from same origin or data URLs
- **connect-src**: XHR/WebSocket from same origin, secure WebSocket
- **frame-ancestors 'none'**: Cannot be embedded in iframes
- **base-uri 'self'**: Base URL can only be same origin
- **form-action 'self'**: Forms can only submit to same origin

**Protection Against**: Cross-Site Scripting (XSS), data injection attacks

**Notes**: 'unsafe-inline' and 'unsafe-eval' are enabled for React compatibility. Consider nonce-based CSP in production:
```
script-src 'self' 'nonce-{random-value}'
```

### 3. X-Content-Type-Options

```
X-Content-Type-Options: nosniff
```

**Purpose**: Prevent MIME type sniffing
- Instructs browser to trust the Content-Type header
- Prevents execution of scripts with wrong MIME type

**Protection Against**: MIME type confusion attacks, drive-by downloads

**Browser Support**: All modern browsers

### 4. X-Frame-Options

```
X-Frame-Options: SAMEORIGIN
```

**Purpose**: Prevent clickjacking attacks
- **SAMEORIGIN**: Page can only be embedded in same origin
- Alternatives: DENY (never embed), ALLOW-FROM (specific origin - deprecated)

**Protection Against**: Clickjacking, UI redressing attacks

**Browser Support**: All modern browsers

### 5. X-XSS-Protection

```
X-XSS-Protection: 1; mode=block
```

**Purpose**: Legacy XSS protection for older browsers
- **1**: Enable XSS filter
- **mode=block**: Block page instead of sanitizing
- Modern browsers prefer CSP, but this helps older browsers

**Browser Support**: IE, older Chrome/Safari/Edge

### 6. Referrer-Policy

```
Referrer-Policy: strict-origin-when-cross-origin
```

**Purpose**: Control when Referer header is sent
- **strict-origin-when-cross-origin**:
  - Full URL when same origin
  - Only origin (scheme + domain) on cross-origin
  - No referrer on HTTP → HTTPS downgrade

**Protection Against**: Information leakage, privacy concerns

**Other Options**:
- `no-referrer`: Never send Referer
- `same-origin`: Only send same-origin
- `strict-origin`: Only origin, no downgrade

### 7. Permissions-Policy (formerly Feature-Policy)

```
Permissions-Policy: geolocation=(),
                   microphone=(),
                   camera=(),
                   payment=(),
                   usb=(),
                   magnetometer=(),
                   gyroscope=(),
                   accelerometer=()
```

**Purpose**: Disable access to device APIs
- Each directive set to `()` means disabled for all contexts
- Syntax: `api=(*|self|"<origin>")`

**Disabled APIs**:
- geolocation: GPS access
- microphone: Audio recording
- camera: Video recording
- payment: Payment API
- usb: USB device access
- magnetometer: Compass/magnetic sensor
- gyroscope: Motion sensor
- accelerometer: Acceleration sensor

**Protection Against**: Unauthorized device access, privacy violations

### 8. Cross-Origin-Opener-Policy (COOP)

```
Cross-Origin-Opener-Policy: same-origin
```

**Purpose**: Isolate global window object
- Prevents cross-origin pages from opening the site in new windows
- **same-origin**: Only same-origin can be in opener relationship

**Protection Against**: Spectre attacks, cross-site data leakage

**Browser Support**: Chrome 74+, Firefox 79+, Safari 15.2+

### 9. Cross-Origin-Embedder-Policy (COEP)

```
Cross-Origin-Embedder-Policy: require-corp
```

**Purpose**: Require CORS/CORP headers for embedded resources
- **require-corp**: Embedded resources must have CORS/CORP headers
- Enables `SharedArrayBuffer` and `Performance.measureUserAgentSpecificMemory()`

**Protection Against**: Spectre attacks, timing attacks

**Note**: May break embedded resources that lack proper CORS headers

### 10. Cross-Origin-Resource-Policy (CORP)

```
Cross-Origin-Resource-Policy: same-origin
```

**Purpose**: Restrict who can load this resource
- **same-origin**: Only same-origin can load
- Alternatives: same-site, cross-origin

**Protection Against**: Cross-site data leakage, resource theft

## Additional Security Measures

### Hidden Server Version
```nginx
server_tokens off;
```
- Hides nginx version in error pages and Server header
- Reduces surface area for version-specific exploits

### Disabled Directory Listing
```nginx
autoindex off;
```
- Prevents directory contents from being listed
- Denies access if no default file exists

### Gzip Compression
```nginx
gzip on;
gzip_comp_level 6;
gzip_types ...;
```
- Compresses responses by 60-80%
- Faster page loads, reduced bandwidth
- Configured for text, JavaScript, JSON, fonts

### Cache Busting
```nginx
# Files with hash in name: cache for 1 year
location ~* ^/assets/.*\.[a-f0-9]{8,}\.(js|css|...)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}

# Regular assets: cache for 30 days
location ~* \.(js|css|...)$ {
    expires 30d;
}
```

### Sensitive File Protection
```nginx
# Block .env, .git, .htaccess, backups
location ~ /\. { deny all; }
location ~ \.env { deny all; }
location ~ /\.git { deny all; }
location ~ \.(bak|backup|sql|zip)$ { deny all; }

# Block vulnerability scanning paths
location ~ (wp-admin|wp-login|xmlrpc\.php) { deny all; }

# Block node_modules and source maps
location ~ /node_modules { deny all; }
location ~ \.map$ { deny all; }
```

## Testing Security Headers

### Using curl
```bash
curl -I https://the-bot.ru
```

### Using Security Header Scanner
Visit [securityheaders.com](https://securityheaders.com) and enter your domain:
1. Provides detailed security grade (A-F)
2. Lists all headers present/missing
3. Explains each header
4. Provides remediation advice

### Using test-security-headers.sh
```bash
chmod +x frontend/test-security-headers.sh
./frontend/test-security-headers.sh the-bot.ru https
```

### Testing CSP Violations
To verify CSP is working, open browser DevTools Console and try:
```javascript
// Should be blocked by CSP
eval("alert('This should be blocked by CSP')");
```

### Checking HSTS
1. Visit https://the-bot.ru (should redirect from HTTP)
2. Check response headers for: `Strict-Transport-Security: max-age=31536000`
3. Clear HSTS data in browser settings to reset

## Security Headers Grade Explanation

| Grade | Requirements |
|-------|--------------|
| A+ | All critical headers present, proper config |
| A | Most critical headers present |
| B | Some headers missing, basic protection |
| C | Minimal headers, weak protection |
| D | Very few headers, poor protection |
| F | No security headers configured |

## OWASP Top 10 Coverage

| Vulnerability | Header | Status |
|--------------|--------|--------|
| XSS | CSP, X-XSS-Protection | MITIGATED |
| Clickjacking | X-Frame-Options | PROTECTED |
| MIME Confusion | X-Content-Type-Options | PROTECTED |
| MITM | HSTS | PROTECTED |
| Unauthorized Access | CSP, CORP | MITIGATED |
| Injection | CSP | MITIGATED |
| Broken Auth | HSTS | PROTECTED |
| Sensitive Data Exposure | HSTS, CORP | PROTECTED |
| Component Vulnerabilities | CSP | MITIGATED |
| Security Misconfiguration | All Headers | ADDRESSED |

## Future Enhancements

### Subresource Integrity (SRI)
When external scripts/styles are used:
```html
<script src="https://cdn.example.com/lib.js"
        integrity="sha384-{hash}"
        crossorigin="anonymous"></script>
```

### Nonce-Based CSP
For production, replace inline script permissions with nonce:
```nginx
add_header Content-Security-Policy "script-src 'nonce-{random}'" always;
```

Then in HTML:
```html
<script nonce="{random}">
  // Inline script
</script>
```

### Report-Only Mode
Test CSP changes before enforcing:
```nginx
add_header Content-Security-Policy-Report-Only "...";
```

### Reporting Endpoint
Add CSP violation reporting:
```
Content-Security-Policy: ...; report-uri /api/csp-report;
```

## References

- [OWASP: Secure Headers](https://owasp.org/www-project-secure-headers/)
- [MDN: HTTP Headers](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers)
- [Mozilla: Web Security Guidelines](https://infosec.mozilla.org/guidelines/web_security)
- [NIST: Web Application Security](https://csrc.nist.gov/publications/detail/sp/800-95/final)

## Maintenance

### Monthly Audit
1. Run `test-security-headers.sh` monthly
2. Check [securityheaders.com](https://securityheaders.com)
3. Review security news for new best practices

### When to Update
- New vulnerability disclosed
- Browser requirements change
- Third-party dependencies added
- CSP violations reported

## Support

For issues or questions about security headers:
1. Check browser Console for CSP violations
2. Run `test-security-headers.sh` for diagnostics
3. Review nginx error logs
4. Check [securityheaders.com](https://securityheaders.com) for analysis

---

Last Updated: December 27, 2025
Configuration Version: 1.0
