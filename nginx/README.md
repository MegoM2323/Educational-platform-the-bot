# Nginx Configuration for THE BOT Platform

## File Structure

```
nginx/
├── the-bot.ru.conf      # Main production nginx configuration
├── ssl.conf             # SSL/TLS configuration (included by main config)
└── README.md            # This file
```

## Main Configuration File

### `the-bot.ru.conf`

Production Nginx configuration for THE BOT platform with:

- **SSL/TLS Setup**: Let's Encrypt certificates with automatic renewal
- **Security**: HSTS, CSP, X-Frame-Options, and other security headers
- **Performance**: Gzip compression, caching, session management
- **Routing**: API, WebSocket, admin panel, media files, static assets
- **Upstreams**: Daphne (Django ASGI), Django (REST API)

#### Installation

```bash
# Copy to nginx sites-available
sudo cp the-bot.ru.conf /etc/nginx/sites-available/the-bot.ru

# Create symlink to sites-enabled
sudo ln -s /etc/nginx/sites-available/the-bot.ru /etc/nginx/sites-enabled/the-bot.ru

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

#### Key Sections

1. **HTTP Redirect Server** (port 80)
   - Redirects all HTTP to HTTPS
   - Serves ACME challenges for Let's Encrypt renewal

2. **HTTPS Server** (port 443)
   - SSL/TLS configuration
   - Security headers
   - Proxy routing to upstream services
   - Static file serving

#### Upstream Services

- **Daphne** (port 8001): Django ASGI (WebSocket, API, admin)
- **Django** (port 8000): Django REST API (backup)

#### Location Routing

| Path | Upstream | Purpose |
|------|----------|---------|
| `/api/` | Daphne | REST API endpoints |
| `/admin/` | Daphne | Django admin panel |
| `/ws/` | Daphne | WebSocket connections |
| `/media/` | Daphne | Media files (authenticated) |
| `/yookassa-webhook/` | Daphne | Payment webhooks |
| `/` | Static/Daphne | Frontend files or React Router |

## SSL/TLS Configuration

### `ssl.conf`

Dedicated SSL/TLS configuration file with:

- **Protocol Configuration**: TLS 1.2+, weak protocols disabled
- **Cipher Suites**: Modern ECDHE ciphers with forward secrecy
- **Session Management**: Shared cache, optimized timeouts
- **OCSP Stapling**: Improved certificate validation performance
- **Certificate Pinning**: Optional (commented out by default)

#### Protocols

✓ TLS 1.2, TLS 1.3
✗ SSLv3, TLS 1.0, TLS 1.1 (disabled)

#### Ciphers

Ordered by preference:
1. ECDHE-ECDSA-AES128-GCM-SHA256
2. ECDHE-RSA-AES256-GCM-SHA384
3. ECDHE-ECDSA-CHACHA20-POLY1305
4. DHE-RSA-AES256-GCM-SHA384

All ciphers support:
- Forward secrecy (ECDHE/DHE)
- Authenticated encryption (GCM/POLY1305)
- Strong key sizes (128-256 bits)

#### Usage

Include in nginx configuration:

```nginx
server {
    listen 443 ssl http2;
    server_name the-bot.ru www.the-bot.ru;

    # Include SSL configuration
    include /path/to/ssl.conf;

    # Other directives...
}
```

## Certificates

### Location

Certificates are stored at: `/etc/letsencrypt/live/the-bot.ru/`

Files:
- `cert.pem`: Server certificate
- `privkey.pem`: Private key (KEEP SECRET!)
- `chain.pem`: Intermediate certificates
- `fullchain.pem`: cert + chain (used by Nginx)

### Permissions

```bash
# Check certificate permissions
ls -la /etc/letsencrypt/live/the-bot.ru/

# Should be readable by nginx user
# privkey.pem is typically root:root 0600
```

### Renewal

Certificates are automatically renewed via systemd timer:

```bash
# Check renewal status
sudo systemctl status certbot.timer

# View renewal schedule
sudo systemctl list-timers certbot.timer

# Manual renewal
sudo certbot renew
```

## Security Features

### HSTS (HTTP Strict Transport Security)

```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
```

- Enforces HTTPS for 1 year
- Applies to all subdomains
- Allows HSTS preload inclusion

### CSP (Content-Security-Policy)

Prevents XSS attacks:
- `default-src 'self'`: Only load from same origin
- `script-src 'self' 'unsafe-inline'`: Allow inline scripts (React)
- `connect-src 'self' wss: ws:`: Allow API and WebSocket

### Other Headers

- `X-Frame-Options: SAMEORIGIN`: Prevents clickjacking
- `X-Content-Type-Options: nosniff`: Prevents MIME type sniffing
- `Referrer-Policy: strict-origin-when-cross-origin`: Controls referrer info
- `Permissions-Policy`: Disables unnecessary APIs

## Performance

### Gzip Compression

```nginx
gzip on;
gzip_min_length 1000;      # Compress files > 1KB
gzip_comp_level 6;         # Balance speed/compression
gzip_types: text, json, javascript, css, fonts
```

### Caching

- **Hashed assets** (e.g., `app.abc123def.js`): Cache 1 year
- **Regular assets** (e.g., `index.html`): Cache 30 days
- **Static files**: 30 day cache with cache busting

### Session Caching

```nginx
ssl_session_cache shared:SSL:40m;   # 40MB shared cache
ssl_session_timeout 1d;             # 1 day timeout
```

## Proxy Configuration

### Headers Forwarded to Upstream

```nginx
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
```

### WebSocket Support

```nginx
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
```

### Timeouts

- **API**: 30s connect, 30s send, 30s read
- **Admin**: 60s connect, 60s send, 60s read
- **Media**: 120s send/read (large files)
- **WebSocket**: 86400s (1 day, permanent connections)

## Logging

### Log Files

- **Access log**: `/var/log/nginx/the-bot-access.log`
- **Error log**: `/var/log/nginx/the-bot-error.log`

### Log Format

```
combined format: IP, timestamp, request, status, bytes, referer, user-agent
```

Some locations log is disabled:
- Static assets (hashed, frequently accessed)
- Sensitive files (`.env`, `.git`)
- Vulnerability scanners (wp-admin, xmlrpc)

## Troubleshooting

### Test Configuration

```bash
# Test nginx configuration syntax
sudo nginx -t

# Detailed error output
sudo nginx -t -v

# Check if nginx will reload successfully
sudo nginx -s reload -c /etc/nginx/nginx.conf
```

### Check Logs

```bash
# View error log
sudo tail -50 /var/log/nginx/the-bot-error.log

# Follow error log in real-time
sudo tail -f /var/log/nginx/the-bot-error.log

# View access log
sudo tail -50 /var/log/nginx/the-bot-access.log

# Check specific response codes
sudo grep "500\|502\|503" /var/log/nginx/the-bot-error.log
```

### Restart Services

```bash
# Reload configuration (graceful)
sudo systemctl reload nginx

# Full restart
sudo systemctl restart nginx

# Check status
sudo systemctl status nginx

# View recent errors
sudo journalctl -u nginx -n 50
```

### Check Port Bindings

```bash
# Check if port 80 is listening
sudo ss -tlnp | grep :80

# Check if port 443 is listening
sudo ss -tlnp | grep :443

# Check what's using a port
sudo lsof -i :8000
```

### SSL/TLS Diagnostics

```bash
# Test TLS 1.2
openssl s_client -tls1_2 -connect the-bot.ru:443

# Test TLS 1.3
openssl s_client -tls1_3 -connect the-bot.ru:443

# View certificate
openssl s_client -connect the-bot.ru:443 | openssl x509 -text -noout

# Check certificate expiration
openssl x509 -in /etc/letsencrypt/live/the-bot.ru/cert.pem -text -noout | grep -E "Not Before|Not After"
```

## Security Best Practices

### 1. Hide Nginx Version

```nginx
server_tokens off;   # Don't reveal nginx version in headers
```

### 2. Disable Unnecessary Features

```nginx
autoindex off;       # Don't show directory listings
```

### 3. Deny Access to Sensitive Files

Configured to deny:
- Hidden files/directories (`.env`, `.git`)
- Backup files (`.bak`, `.backup`)
- Source maps (`.map`)
- Node modules

### 4. Rate Limiting (In Backend)

- Login: 5 attempts/minute per IP
- Brute force: Lock after 10 failures
- Handled by Django, not nginx

### 5. Monitor Certificates

```bash
# Setup cron job for monitoring
0 0 * * * /path/to/scripts/ssl-monitor.sh check >> /var/log/ssl-monitor.log 2>&1
```

## Maintenance

### Weekly

```bash
# Check error logs
sudo tail -100 /var/log/nginx/the-bot-error.log

# Monitor certificate
bash scripts/ssl-monitor.sh check
```

### Monthly

```bash
# Review access logs
sudo tail -1000 /var/log/nginx/the-bot-access.log | less

# Check certificate expiration
bash scripts/ssl-monitor.sh status
```

### As Needed

```bash
# Update configuration
sudo cp /tmp/the-bot.ru.conf /etc/nginx/sites-available/the-bot.ru
sudo nginx -t
sudo systemctl reload nginx

# Renew certificate
sudo bash scripts/ssl-monitor.sh renew-dry
sudo bash scripts/ssl-monitor.sh renew
```

## References

- [Nginx Documentation](https://nginx.org/en/docs/)
- [Let's Encrypt](https://letsencrypt.org/)
- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/)
- [OWASP: Secure Headers](https://cheatsheetseries.owasp.org/cheatsheets/Secure_Headers_Cheat_Sheet.html)

## Support Scripts

Related scripts in `/scripts/`:

- `setup-ssl.sh`: Initial SSL setup with Let's Encrypt
- `ssl-monitor.sh`: Certificate monitoring and renewal
- `test-ssl.sh`: SSL/TLS testing and validation

See `docs/SSL_TLS_CONFIGURATION.md` for full documentation.
