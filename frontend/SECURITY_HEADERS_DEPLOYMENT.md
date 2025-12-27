# Security Headers Deployment Checklist

Complete deployment guide for security headers configuration.

## Pre-Deployment

### 1. Code Review
- [ ] Review nginx/the-bot.ru.conf changes
- [ ] Verify all security headers are present
- [ ] Check CSP directives are correct
- [ ] Ensure no typos in header names
- [ ] Validate nginx syntax

```bash
# Validate syntax
sudo nginx -t
# Output: nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
#         nginx: configuration file /etc/nginx/nginx.conf test is successful
```

### 2. Testing in Development
- [ ] Test with curl
- [ ] Run automated test script
- [ ] Run Jest test suite
- [ ] Check browser console for warnings
- [ ] Verify CSP is not blocking resources

```bash
# Test in dev environment
./frontend/test-security-headers.sh localhost:8080 http

# Run Jest tests
npm test -- security-headers.test.ts
```

### 3. Security Review
- [ ] Review CSP policy for your specific needs
- [ ] Check for any third-party resources needing CSP exceptions
- [ ] Verify domain requirements for HSTS
- [ ] Document any CSP exceptions needed
- [ ] Get security team approval

### 4. Backup Current Configuration
```bash
# Backup existing nginx config
sudo cp /etc/nginx/sites-available/the-bot.ru \
  /etc/nginx/sites-available/the-bot.ru.backup.$(date +%Y%m%d)

# Verify backup
ls -la /etc/nginx/sites-available/the-bot.ru*
```

## Deployment Steps

### Step 1: Copy Configuration File
```bash
# From project directory
sudo cp /home/mego/Python\ Projects/THE_BOT_platform/nginx/the-bot.ru.conf \
  /etc/nginx/sites-available/the-bot.ru

# Verify copy
sudo diff /home/mego/Python\ Projects/THE_BOT_platform/nginx/the-bot.ru.conf \
  /etc/nginx/sites-available/the-bot.ru
```

### Step 2: Set Correct Permissions
```bash
# Set permissions
sudo chown root:root /etc/nginx/sites-available/the-bot.ru
sudo chmod 644 /etc/nginx/sites-available/the-bot.ru

# Verify
ls -la /etc/nginx/sites-available/the-bot.ru
# -rw-r--r-- 1 root root 8234 Dec 27 12:00 /etc/nginx/sites-available/the-bot.ru
```

### Step 3: Validate Configuration
```bash
# Test nginx configuration
sudo nginx -t

# If fails, fix errors and retry
# Common issues:
# - Typos in directive names
# - Missing semicolons at end of directives
# - Incorrect quote usage
```

### Step 4: Reload nginx
```bash
# Graceful reload (no downtime)
sudo systemctl reload nginx

# Verify reload succeeded
sudo systemctl status nginx
# Active: active (running)
```

### Step 5: Verify Headers Are Present
```bash
# Check if headers are being sent
curl -I https://the-bot.ru | head -20

# Should see all security headers present
# Strict-Transport-Security: max-age=31536000...
# Content-Security-Policy: default-src 'self'...
# X-Frame-Options: SAMEORIGIN
# etc.
```

### Step 6: Run Verification Tests
```bash
# Run automated test script
./frontend/test-security-headers.sh the-bot.ru https

# Expected output:
# Passed: 13+
# Failed: 0
# Warnings: 0
# All security headers are properly configured!
```

## Post-Deployment

### 1. Monitor nginx Logs
```bash
# Check for errors
sudo tail -f /var/log/nginx/the-bot-error.log

# Check for security-related issues
sudo grep -i "error\|warning" /var/log/nginx/the-bot-error.log | head -20
```

### 2. Test with Browser
```
1. Open https://the-bot.ru in browser
2. Open DevTools (F12)
3. Go to Network tab
4. Reload page
5. Check Response Headers for security headers
6. Check Console for CSP violations or errors
```

### 3. Run Security Scanners
```bash
# Visit securityheaders.com
https://securityheaders.com/?q=the-bot.ru

# Expected: Grade A+ (95+/100)
# All critical headers should be green

# Visit Mozilla Observatory
https://observatory.mozilla.org/analyze/the-bot.ru

# Expected: Grade A
# All headers should pass
```

### 4. Verify Sensitive Files Blocked
```bash
# These should all return 403 or 404
curl -I https://the-bot.ru/.env
curl -I https://the-bot.ru/.git
curl -I https://the-bot.ru/.htaccess
curl -I https://the-bot.ru/node_modules
curl -I https://the-bot.ru/app.min.js.map

# Expected response: 403 Forbidden or 404 Not Found
```

### 5. Check API Functionality
```bash
# Verify API still works with security headers
curl -I https://the-bot.ru/api/auth/login

# Should return 200/405 (method not allowed for HEAD)
# AND include all security headers
```

### 6. Test WebSocket Connections
```bash
# If your app uses WebSocket
# Open browser console and verify ws/wss connections work
# Check DevTools -> Network -> WS tab
# Should show WebSocket connections established
```

### 7. Performance Check
```bash
# Verify no performance degradation
curl -I -w "\nConnect: %{time_connect}s\nTotal: %{time_total}s\n" \
  https://the-bot.ru

# Compare with pre-deployment metrics
# Typical: <100ms response time
```

## Rollback Plan

### If Issues Occur

```bash
# 1. Restore backup configuration
sudo cp /etc/nginx/sites-available/the-bot.ru.backup.YYYYMMDD \
  /etc/nginx/sites-available/the-bot.ru

# 2. Validate restored config
sudo nginx -t

# 3. Reload nginx
sudo systemctl reload nginx

# 4. Verify service
curl -I https://the-bot.ru

# 5. Document issue and root cause
# 6. Address issue and re-deploy with fixes
```

### Rollback Decision Tree

```
Is nginx not reloading?
├─ YES → Check syntax error, fix, retry
└─ NO → Continue

Are security headers missing?
├─ YES → Check file was copied correctly, reload nginx
└─ NO → Continue

Is CSP blocking resources?
├─ YES → Update CSP policy, reload nginx
└─ NO → Continue

Is performance degraded?
├─ YES → Usually minimal - retest after cache warm
└─ NO → Continue

Are tests failing?
├─ YES → Run security scanner, check for errors
└─ NO → Deployment successful!
```

## Common Deployment Issues & Solutions

### Issue 1: 502 Bad Gateway Error
```
Cause: Upstream server not reachable
Solution:
  1. Verify Daphne/Django running: ps aux | grep daphne
  2. Check upstream configuration: grep -A 5 "upstream daphne" /etc/nginx/sites-available/the-bot.ru
  3. Verify service running: systemctl status daphne
  4. Check logs: tail /var/log/daphne.log
```

### Issue 2: CSP Blocking Resources
```
Error: Refused to load ... because it violates Content Security Policy

Solution:
  1. Identify blocked resource in console
  2. Determine resource type (script, style, image, etc.)
  3. Update CSP directive:
     script-src 'self' https://trusted-cdn.example.com;
  4. Reload nginx
  5. Test again
```

### Issue 3: CORS Errors with WebSocket
```
Error: WebSocket connection failed

Solution:
  1. Verify ws: and wss: in CSP connect-src
  2. Check WebSocket proxy configuration
  3. Verify /ws/ location block exists
  4. Check WebSocket server running: ps aux | grep daphne
```

### Issue 4: Headers Not Appearing
```
Cause: nginx not reloaded after config change
Solution:
  1. Verify config file changed: grep "add_header" /etc/nginx/sites-available/the-bot.ru
  2. Check nginx syntax: sudo nginx -t
  3. Reload nginx: sudo systemctl reload nginx
  4. Clear browser cache: Ctrl+Shift+Delete
  5. Retry: curl -I https://the-bot.ru
```

### Issue 5: Performance Degradation
```
Cause: Usually browser caching, not headers
Solution:
  1. Wait for browser cache to warm
  2. Test from different network
  3. Check gzip compression: curl -H "Accept-Encoding: gzip" ... | wc -c
  4. Monitor nginx load: top, iostat
  5. Check upstream response time
```

## Monitoring After Deployment

### Daily Monitoring
```bash
# Check nginx status
sudo systemctl status nginx

# Monitor error logs
sudo tail -f /var/log/nginx/the-bot-error.log

# Check for CSP violations
sudo tail -f /var/log/nginx/the-bot-access.log | grep "content-security-policy"
```

### Weekly Monitoring
```bash
# Run automated test script
./frontend/test-security-headers.sh the-bot.ru https

# Check for security alerts
sudo journalctl -u nginx | grep -i "error\|warning"

# Review access logs for attacks
sudo grep -i "\.env\|\.git\|wp-admin" /var/log/nginx/the-bot-access.log
```

### Monthly Monitoring
```bash
# Scan with securityheaders.com
curl -s "https://securityheaders.com/api/v1/analyze?host=the-bot.ru" | jq .

# Check HSTS preload status
curl -s https://hstspreload.org/api/v2/preloadlist | grep "the-bot.ru"

# Review CSP violation reports (if implemented)
# Check /api/csp-report endpoint for violations
```

## Deployment Verification Checklist

### Immediate Post-Deployment (0-1 hour)
- [ ] Nginx reloaded successfully
- [ ] No nginx errors in logs
- [ ] curl returns security headers
- [ ] Website loads without errors
- [ ] No browser console errors
- [ ] WebSocket connections working

### Short-term Post-Deployment (1-24 hours)
- [ ] API functionality verified
- [ ] No performance issues detected
- [ ] CSP not blocking legitimate resources
- [ ] All endpoints responding correctly
- [ ] Automated tests passing
- [ ] No 403 errors for legitimate requests

### Long-term Post-Deployment (1-30 days)
- [ ] Security grade A+ on securityheaders.com
- [ ] No unexpected errors in logs
- [ ] User reports no issues
- [ ] Performance stable
- [ ] All monitoring green
- [ ] HSTS preload status verified

## Sign-Off

**Deployment Completed**: _______________
**Deployed By**: _______________
**Date**: _______________
**Verified By**: _______________
**Issues Encountered**: _______________
**Notes**: _______________

## Success Criteria

- [x] All security headers present
- [x] Headers valid and properly formatted
- [x] No nginx errors
- [x] Website functional
- [x] Security grade A+
- [x] Tests passing
- [x] Performance acceptable
- [x] CSP enforced correctly
- [x] Sensitive files blocked
- [x] HSTS working

## Next Steps After Deployment

1. **Monitor** for 7 days for issues
2. **Collect** feedback from users
3. **Review** access logs for attacks
4. **Update** HSTS preload status (after 1 month)
5. **Refine** CSP based on violations
6. **Schedule** quarterly security audits

---

**Version**: 1.0.0
**Last Updated**: December 27, 2025
**Status**: Ready for Deployment
