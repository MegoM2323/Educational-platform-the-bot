# Security Headers Testing Guide

Complete guide for testing and verifying security headers configuration for THE_BOT Platform.

## Quick Start

### 1. Verify Headers Are Present (Production)

```bash
# Test against production domain
./frontend/test-security-headers.sh the-bot.ru https

# Or with custom domain
./frontend/test-security-headers.sh yourdomain.com https
```

### 2. Manual Header Verification

```bash
# View all response headers
curl -I https://the-bot.ru

# Check specific header
curl -I https://the-bot.ru | grep -i "Strict-Transport-Security"

# Full header dump (useful for debugging)
curl -v https://the-bot.ru 2>&1 | head -30
```

### 3. Web-Based Security Scanner

Visit [securityheaders.com](https://securityheaders.com) and enter your domain:
1. Click "Scan"
2. Review detailed analysis
3. Grade: A+ (excellent), A (good), B-F (needs improvement)

## Detailed Testing Methods

### Using curl

#### Test All Headers at Once
```bash
curl -I https://the-bot.ru > headers.txt
cat headers.txt
```

Output should include:
```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
Content-Security-Policy: default-src 'self'; ...
X-Frame-Options: SAMEORIGIN
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=(), ...
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Embedder-Policy: require-corp
Cross-Origin-Resource-Policy: same-origin
```

#### Test Individual Headers
```bash
# HSTS
curl -s -I https://the-bot.ru | grep -i "strict-transport"

# CSP
curl -s -I https://the-bot.ru | grep -i "content-security-policy"

# Clickjacking Protection
curl -s -I https://the-bot.ru | grep -i "x-frame-options"

# MIME Sniffing Prevention
curl -s -I https://the-bot.ru | grep -i "x-content-type-options"

# XSS Protection
curl -s -I https://the-bot.ru | grep -i "x-xss-protection"
```

#### Check for Server Version Leakage
```bash
curl -s -I https://the-bot.ru | grep -i "server"

# Should return minimal info or nothing, not "nginx/1.25.3"
```

### Using Browser Developer Tools

#### 1. Firefox Developer Tools
1. Open DevTools (F12)
2. Go to Network tab
3. Reload page
4. Click on document request (first request)
5. Go to Response Headers tab
6. Verify all security headers are present

#### 2. Chrome Developer Tools
1. Open DevTools (F12)
2. Go to Network tab
3. Reload page
4. Click on document request
5. Scroll down to Response Headers
6. Verify all security headers are present

#### 3. Browser Console for CSP Violations
1. Open DevTools Console (F12)
2. Look for messages like: `Refused to load script ... Content Security Policy`
3. This indicates CSP is enforcing policies correctly

### Using Online Security Scanners

#### securityheaders.com
```bash
# Visit URL in browser
https://securityheaders.com/?q=the-bot.ru

# Or use curl to get JSON results
curl -s "https://securityheaders.com/api/v1/analyze?host=the-bot.ru&followRedirects=true" | jq .
```

Returns:
- **grade**: A+, A, B, C, D, F
- **score**: 0-100
- **details**: Each header status

#### Mozilla Observatory
```bash
# Visit URL in browser
https://observatory.mozilla.org/analyze/the-bot.ru

# Or use curl
curl -s https://api.observatory.mozilla.org/api/v1/analyze?host=the-bot.ru | jq .
```

### Testing CSP Violations

#### Method 1: Console Test
Open browser console and run:
```javascript
// This should be blocked by CSP (unless unsafe-eval is set)
eval("alert('CSP Test')");

// This should be blocked
var xss = '<img src=x onerror="alert(\'XSS\')">';
document.body.innerHTML = xss;
```

Expected: Browser blocks execution and logs CSP violation

#### Method 2: Test Page
Create test.html with CSP violation:
```html
<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="Content-Security-Policy"
          content="default-src 'self'">
</head>
<body>
    <!-- This will be blocked by CSP -->
    <script>
        // This should be blocked
        alert('Inline script');
    </script>
</body>
</html>
```

#### Method 3: Check Console Logs
1. Open DevTools Console
2. Reload page
3. Look for CSP violation reports:
   ```
   Refused to load script 'inline' because it violates the following Content Security Policy directive: "default-src 'self'"
   ```

### Testing HSTS

#### Verify HSTS Header
```bash
curl -I https://the-bot.ru | grep -i "strict-transport"

# Output should include:
# Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
```

#### Test HSTS Preload
```bash
# Check if domain is in HSTS preload list
curl -s https://chromium.googlesource.com/chromium/src/+/main/net/http/transport_security_state_static.json \
  | grep "the-bot.ru"

# Or visit
https://hstspreload.org/?domain=the-bot.ru
```

#### Manual HSTS Test
1. Visit http://the-bot.ru (HTTP, not HTTPS)
2. Should redirect to HTTPS
3. Check Response Headers:
   ```
   Location: https://the-bot.ru
   Strict-Transport-Security: max-age=31536000; ...
   ```
4. Once HSTS is cached in browser, subsequent HTTP requests are automatically upgraded

### Testing Cache Busting

#### Check Static Asset Caching
```bash
# Check cache headers for versioned file
curl -I https://the-bot.ru/assets/app.a1b2c3d4.js | grep -i "cache-control"

# Output should be:
# Cache-Control: public, immutable

# For non-versioned files
curl -I https://the-bot.ru/index.html | grep -i "cache-control"

# Output should be:
# Cache-Control: no-cache, no-store, must-revalidate
```

### Testing Gzip Compression

```bash
# Test gzip compression
curl -I -H "Accept-Encoding: gzip" https://the-bot.ru | grep -i "content-encoding"

# Output should be:
# Content-Encoding: gzip
```

### Testing Sensitive File Blocking

```bash
# These should all return 403 or 404
curl -I https://the-bot.ru/.env
curl -I https://the-bot.ru/.git
curl -I https://the-bot.ru/.htaccess
curl -I https://the-bot.ru/node_modules
curl -I https://the-bot.ru/app.min.js.map
curl -I https://the-bot.ru/wp-admin
curl -I https://the-bot.ru/backup.sql
```

Expected response: `403 Forbidden` or `404 Not Found`

## Automated Testing

### Run Test Script
```bash
# Make executable
chmod +x frontend/test-security-headers.sh

# Run against your domain
./frontend/test-security-headers.sh the-bot.ru https

# Run against localhost (development)
./frontend/test-security-headers.sh localhost:8080 http
```

Output example:
```
========================================
Security Headers Verification Test
Testing: https://the-bot.ru
========================================

Testing Strict-Transport-Security... PRESENT
  Value: max-age=31536000; includeSubDomains; preload

Testing Content-Security-Policy... PRESENT
  Value: default-src 'self'; script-src 'self' 'unsafe-inline'; ...

...

========================================
Test Summary
========================================
Passed: 18
Failed: 0
Warnings: 0

All security headers are properly configured!
```

### Jest Test Suite
```bash
# Install dependencies
cd frontend
npm install

# Run security headers tests
npm test -- security-headers.test.ts

# Run with coverage
npm test -- security-headers.test.ts --coverage

# Run in watch mode
npm test -- security-headers.test.ts --watch
```

## Troubleshooting

### Header Not Present

**Problem**: Security header shows as missing
```
Testing Content-Security-Policy... MISSING
```

**Solution**:
1. Verify nginx configuration:
   ```bash
   grep -n "Content-Security-Policy" /etc/nginx/sites-available/the-bot.ru
   ```
2. Check syntax:
   ```bash
   sudo nginx -t
   ```
3. Reload nginx:
   ```bash
   sudo systemctl reload nginx
   ```
4. Wait a moment and retry test

### CSP Blocking Resources

**Problem**: Resources are being blocked by CSP
```
Refused to load [resource] because it violates Content Security Policy
```

**Solution**:
1. Identify blocked resource type (script, style, image, etc.)
2. Update CSP to allow it:
   ```nginx
   # For external scripts
   script-src 'self' https://trusted-cdn.example.com;

   # For inline styles
   style-src 'self' 'unsafe-inline';
   ```
3. Use nonce for inline scripts:
   ```html
   <script nonce="random-value">
     // Inline script
   </script>
   ```

### HSTS Not Working

**Problem**: HSTS header not being served
```
curl -I http://the-bot.ru | grep -i strict-transport
# Returns nothing
```

**Solution**:
1. HSTS only works over HTTPS:
   ```bash
   curl -I https://the-bot.ru | grep -i strict-transport
   # Should show header
   ```
2. Wait 1 month before HSTS preload list is updated:
   ```
   max-age=31536000 = 1 year cache
   ```

### Server Version Leaking

**Problem**: Server header shows version information
```
curl -I https://the-bot.ru | grep Server
# Server: nginx/1.25.3
```

**Solution**:
1. Add to nginx config:
   ```nginx
   server_tokens off;
   ```
2. Reload nginx:
   ```bash
   sudo systemctl reload nginx
   ```

## Security Headers Checklist

- [ ] HSTS header present and configured
- [ ] CSP header present and restrictive
- [ ] X-Frame-Options set to SAMEORIGIN
- [ ] X-Content-Type-Options set to nosniff
- [ ] X-XSS-Protection enabled
- [ ] Referrer-Policy configured
- [ ] Permissions-Policy restricts APIs
- [ ] COOP/COEP headers present
- [ ] CORP header restricts cross-origin
- [ ] Server version hidden
- [ ] Directory listing disabled
- [ ] Sensitive files blocked (.env, .git, etc.)
- [ ] Cache headers configured properly
- [ ] Gzip compression enabled
- [ ] HTTPS redirect working
- [ ] All tests passing (test-security-headers.sh)
- [ ] securityheaders.com grade A or higher

## Performance Impact

Security headers have minimal performance impact:
- Headers add <1KB to response size
- No computational overhead
- Gzip compression saves 60-80% bandwidth
- Cache-Control reduces requests for static assets

## Browser Support

| Header | Chrome | Firefox | Safari | IE |
|--------|--------|---------|--------|-----|
| HSTS | 4+ | 4+ | 7+ | - |
| CSP | 25+ | 23+ | 7+ | - |
| X-Frame-Options | 4+ | 3.6+ | 4+ | 8+ |
| X-Content-Type-Options | 18+ | 50+ | 7+ | 8+ |
| X-XSS-Protection | 4+ | - | 6+ | 8+ |
| Referrer-Policy | 61+ | 50+ | 11.1+ | - |
| Permissions-Policy | 88+ | 89+ | 16+ | - |
| COOP | 74+ | 79+ | 15.2+ | - |

## Monitoring

### Monthly Checks
- Run test script
- Check securityheaders.com
- Review browser console for CSP violations
- Check nginx error logs

### Alerting
Set up monitoring for:
- Missing security headers
- CSP violations
- HTTPS downgrade attempts
- Suspicious access patterns

## References

- [OWASP: Secure Headers Project](https://owasp.org/www-project-secure-headers/)
- [MDN: HTTP Headers](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers)
- [Mozilla: Web Security Guidelines](https://infosec.mozilla.org/guidelines/web_security)
- [securityheaders.com](https://securityheaders.com)
- [mozilla.org/Observatory](https://observatory.mozilla.org)

---

Last Updated: December 27, 2025
Version: 1.0
