# DNS Configuration для the-bot.ru

## Quick Start
- Domain: the-bot.ru
- IP Address: 5.129.249.206
- Record Type: A
- TTL: 3600 (1 hour) или default у провайдера

## DNS Records Required

### Primary A Record
```
Type: A
Name: the-bot.ru (or @ для root domain)
Value: 5.129.249.206
TTL: 3600
```

### WWW Subdomain (optional)
```
Type: A
Name: www.the-bot.ru
Value: 5.129.249.206
TTL: 3600
```

### API Subdomain (optional)
```
Type: CNAME
Name: api.the-bot.ru
Value: the-bot.ru
TTL: 3600
```

## Validation Commands

### Test DNS Resolution
```bash
# Linux/Mac
nslookup the-bot.ru
dig the-bot.ru +short
host the-bot.ru

# Should return: 5.129.249.206
```

### Test HTTP Connectivity
```bash
curl -v http://the-bot.ru/
curl -v https://the-bot.ru/api/
```

### Test with nc (port check)
```bash
nc -zv the-bot.ru 80
nc -zv the-bot.ru 443
```

## DNS Providers Configuration

### Yandex Cloud DNS
1. Log in to Yandex Cloud
2. Go to DNS → Zone Management
3. Add A record:
   - Name: the-bot.ru
   - Type: A
   - Value: 5.129.249.206
   - TTL: 3600
4. Save and wait for propagation (5-10 min)

### AWS Route 53
1. Log in to AWS Console
2. Route 53 → Hosted Zones
3. Create/Select zone for the-bot.ru
4. Create Record:
   - Name: the-bot.ru
   - Type: A
   - Value: 5.129.249.206
   - TTL: 300
5. Save

### Cloudflare
1. Log in to Cloudflare
2. Add site → the-bot.ru
3. DNS Records:
   - Type: A
   - Name: the-bot.ru
   - IPv4: 5.129.249.206
   - TTL: Auto
4. Turn on proxy (if desired)

## SSL/TLS Certificates

### Let's Encrypt (Certbot)
```bash
# On server (5.129.249.206)
sudo apt-get install certbot python3-certbot-nginx

# Get certificate for domain
sudo certbot certonly --standalone -d the-bot.ru -d www.the-bot.ru

# Update Nginx config with certificate paths
# cert: /etc/letsencrypt/live/the-bot.ru/fullchain.pem
# key: /etc/letsencrypt/live/the-bot.ru/privkey.pem
```

## Health Checks

### Pre-deployment
Before going live, verify:
1. DNS resolves: `nslookup the-bot.ru` returns 5.129.249.206
2. Port 80 open: `curl http://the-bot.ru/`
3. Port 443 open: `curl https://the-bot.ru/`
4. API responds: `curl https://the-bot.ru/api/system/health/live/`

### Post-deployment Monitoring
- Check HTTPS certificate validity
- Monitor DNS propagation globally
- Test from multiple locations
- Verify SSL/TLS is working

## Troubleshooting

### DNS not resolving
- Wait 5-10 minutes for DNS propagation
- Check nameservers: `dig NS the-bot.ru`
- Verify A record is created in DNS provider
- Clear local DNS cache: `sudo dscacheutil -flushcache` (Mac)

### SSL Certificate Issues
- Use `certbot renew` for automatic renewal
- Check certificate expiry: `certbot certificates`
- Verify cert paths in nginx.prod.conf

### Connection Refused
- Verify firewall allows port 80 and 443
- Check Nginx is running: `docker ps | grep nginx`
- Verify ports exposed in docker-compose

## Additional Resources
- DNSSEC: https://en.wikipedia.org/wiki/DNSSEC
- Let's Encrypt: https://letsencrypt.org/
- Cloudflare DNS: https://www.cloudflare.com/dns/
