# GitHub Secrets Setup Guide

This guide explains how to configure GitHub Secrets for the CI/CD pipelines (build, staging, and production deployments).

## Environment Secrets

All secrets should be configured in your GitHub repository settings under **Settings > Secrets and variables > Actions**.

### 1. Container Registry Secrets

#### GITHUB_TOKEN (Automatic)
- **Type**: Automatic
- **Description**: GitHub-provided token for authenticating with GitHub Container Registry (GHCR)
- **Usage**: Build pipeline uses this to push Docker images
- **Setup**: Automatic - no action needed

### 2. SSH Deployment Secrets

#### STAGING_SSH_KEY
- **Type**: Private SSH Key (OpenSSH format)
- **Description**: Private key for SSH access to staging server
- **Usage**: Deploy pipeline uses this to SSH into staging server
- **Setup**:
  ```bash
  # Generate if needed (on your local machine)
  ssh-keygen -t rsa -b 4096 -f staging-key -N ""

  # Convert to OpenSSH format if needed
  ssh-keygen -p -f staging-key -m pem -N "" -M pem

  # Get the private key content
  cat staging-key

  # Copy entire content (including BEGIN/END lines) to GitHub secret
  # Make sure your public key (staging-key.pub) is on the staging server:
  # cat staging-key.pub >> ~/.ssh/authorized_keys
  # chmod 600 ~/.ssh/authorized_keys
  ```
- **Security**:
  - Should be encrypted at rest in GitHub
  - Only accessible to authenticated workflows
  - Rotate quarterly

#### STAGING_HOST
- **Type**: String
- **Description**: Hostname or IP address of staging server
- **Example**: `staging.example.com` or `123.45.67.89`
- **Setup**: Add the hostname/IP address

#### STAGING_USER
- **Type**: String
- **Description**: SSH username for staging server
- **Example**: `deploy` or `ubuntu`
- **Setup**: Add the username

#### STAGING_PATH
- **Type**: String
- **Description**: Deployment path on staging server
- **Example**: `/home/deploy/the-bot` or `/opt/the-bot`
- **Setup**: Add the deployment directory path

#### PRODUCTION_SSH_KEY
- **Type**: Private SSH Key (OpenSSH format)
- **Description**: Private key for SSH access to production server
- **Setup**: Same as STAGING_SSH_KEY
- **Security**: Rotate more frequently (monthly)

#### PRODUCTION_HOST
- **Type**: String
- **Description**: Hostname of production server
- **Example**: `prod.example.com`

#### PRODUCTION_USER
- **Type**: String
- **Description**: SSH username for production server
- **Example**: `deploy`

#### PRODUCTION_PATH
- **Type**: String
- **Description**: Deployment path on production server
- **Example**: `/home/deploy/the-bot`

### 3. Notification Secrets

#### TELEGRAM_BOT_TOKEN
- **Type**: String
- **Description**: Telegram bot token for sending notifications
- **Obtain**:
  1. Create bot with BotFather on Telegram
  2. Get the token (format: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)
- **Setup**: Add token to secrets
- **Usage**: Deploy pipelines notify team of success/failure

#### TELEGRAM_LOG_CHAT_ID
- **Type**: String (Numeric)
- **Description**: Telegram chat ID where notifications are sent
- **Obtain**:
  1. Create private group or use existing chat
  2. Send test message: `/start`
  3. Get chat ID from message updates: `https://api.telegram.org/bot{TOKEN}/getUpdates`
  4. Look for `chat.id` field
- **Example**: `123456789` or `-123456789` (negative for groups)
- **Setup**: Add chat ID to secrets

### 4. API Keys (Optional)

#### VITE_DJANGO_API_URL
- **Type**: String
- **Description**: Frontend environment variable for API URL
- **Example**: `https://api.example.com`
- **Setup**: Add to repository variables (not secrets, these are public)

#### VITE_WEBSOCKET_URL
- **Type**: String
- **Description**: Frontend WebSocket URL
- **Example**: `wss://api.example.com/ws`
- **Setup**: Add to repository variables

### 5. Database Secrets (Not Recommended in GitHub)

**Note**: Database credentials should NOT be stored in GitHub secrets. Instead:
1. Use environment-specific `.env` files on deployment servers
2. Use encrypted secrets management (HashiCorp Vault, AWS Secrets Manager)
3. Use managed database services with temporary credentials

## Step-by-Step Setup

### 1. Go to Repository Settings
```
GitHub → Your Repository → Settings → Secrets and variables → Actions
```

### 2. Add SSH Key Secret
1. Click "New repository secret"
2. Name: `STAGING_SSH_KEY`
3. Value: Paste entire private key (with BEGIN/END lines)
4. Click "Add secret"

### 3. Add SSH Host Secret
1. Click "New repository secret"
2. Name: `STAGING_HOST`
3. Value: `your-staging-server.com`
4. Click "Add secret"

### 4. Repeat for Other Secrets
- STAGING_USER
- STAGING_PATH
- TELEGRAM_BOT_TOKEN
- TELEGRAM_LOG_CHAT_ID
- PRODUCTION_SSH_KEY (if deploying to production)
- PRODUCTION_HOST
- PRODUCTION_USER
- PRODUCTION_PATH

## Testing Secrets

### Test SSH Connection
```bash
# In GitHub Actions workflow
- name: Test SSH Connection
  run: |
    ssh -i ~/.ssh/staging_key \
        ${{ secrets.STAGING_USER }}@${{ secrets.STAGING_HOST }} \
        'echo "SSH connection successful"'
```

### Test Telegram Token
```bash
# In GitHub Actions workflow
- name: Test Telegram Notification
  run: |
    curl -X POST https://api.telegram.org/bot${{ secrets.TELEGRAM_BOT_TOKEN }}/sendMessage \
      -d chat_id=${{ secrets.TELEGRAM_LOG_CHAT_ID }} \
      -d text="Test message"
```

## Security Best Practices

### 1. Rotate Secrets Regularly
- SSH keys: Monthly (production), Quarterly (staging)
- API keys: Quarterly
- Database passwords: Monthly

### 2. Limit Secret Scope
- Use environment-specific secrets
- Staging and production should have separate credentials
- Don't share production secrets with staging workflows

### 3. Monitor Secret Usage
- Review GitHub Actions logs
- Look for any exposed secrets in logs
- Use secret masking (GitHub does this automatically)

### 4. Secure SSH Keys
```bash
# Best practices:
# 1. Generate with strong settings
ssh-keygen -t ed25519 -f key_name -N "passphrase"

# 2. Use separate keys for each environment
# 3. Disable password authentication on servers
# 4. Use SSH agent to manage keys
# 5. Rotate keys every 3 months
```

### 5. GitHub Settings
- Enable branch protection rules
- Require status checks before merge
- Restrict who can approve deployments
- Enable audit logging
- Use GitHub's environment protection rules

## Troubleshooting

### SSH Connection Fails
**Error**: "Permission denied (publickey)"

**Solutions**:
1. Verify public key is on server: `cat ~/.ssh/authorized_keys`
2. Check SSH key format: Must be OpenSSH format
3. Verify SSH user has home directory with .ssh folder
4. Check file permissions: `.ssh` should be 700, `authorized_keys` should be 600

**Test locally**:
```bash
ssh -i ~/staging-key deploy@staging.example.com
```

### Secret Not Found
**Error**: "Secret not found: STAGING_HOST"

**Solutions**:
1. Verify secret exists in Settings → Secrets
2. Check exact spelling and case
3. Secrets are case-sensitive
4. May take a few minutes to propagate

### Telegram Notification Fails
**Error**: "Bad Request: chat not found"

**Solutions**:
1. Verify chat ID is numeric (with or without minus)
2. Check if bot has access to chat (add bot to group)
3. Test with curl locally using correct chat ID
4. Try with different chat ID from getUpdates

## Cleanup & Rotation

### Rotate SSH Key
```bash
# 1. Generate new key
ssh-keygen -t rsa -b 4096 -f new-staging-key -N ""

# 2. Add public key to server
ssh-copy-id -i new-staging-key.pub deploy@staging.example.com

# 3. Update GitHub secret
# Update STAGING_SSH_KEY with new private key

# 4. Verify new key works
ssh -i new-staging-key deploy@staging.example.com

# 5. Remove old key from server
# (ssh to server and remove from authorized_keys)

# 6. Delete local old key
rm old-staging-key old-staging-key.pub
```

### Remove Unused Secrets
1. Go to Settings → Secrets and variables
2. Find unused secret
3. Click delete
4. Confirm

## References

- [GitHub Secrets Documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [SSH Key Setup](https://docs.github.com/en/authentication/connecting-to-github-with-ssh)
- [Environment Protection Rules](https://docs.github.com/en/actions/deployment/protecting-deployments/about-environments)
- [OpenSSH Manual](https://man.openbsd.org/ssh-keygen)
