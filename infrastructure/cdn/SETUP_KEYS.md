# CloudFront Key Generation Guide

This guide explains how to generate CloudFront signing keys for secure media file access.

## What Are Signing Keys?

CloudFront signing keys enable signed URLs that:
- Restrict access to specific files
- Control expiration time
- Prevent URL sharing/abuse
- Ensure only authorized users access media

## Key Pair Generation

### 1. Generate OpenSSL RSA Key Pair

```bash
# Generate private key (2048-bit RSA)
openssl genrsa -out cloudfront-private-key.pem 2048

# Generate public key from private key
openssl rsa -in cloudfront-private-key.pem -pubout -out cloudfront-public-key.pem
```

### 2. Verify Generated Keys

```bash
# Check private key format
openssl rsa -in cloudfront-private-key.pem -text -noout | head -5

# Check public key format
openssl rsa -pubin -in cloudfront-public-key.pem -text -noout | head -5

# Both should show:
# Private-Key: (2048 bit, RSA)
# or
# Public-Key: (2048 bit, RSA)
```

### 3. Secure Key Storage

Place keys in secure location:

```bash
# Create secure directory
sudo mkdir -p /etc/secrets
sudo chmod 700 /etc/secrets

# Move private key (readable only by app user)
sudo mv cloudfront-private-key.pem /etc/secrets/
sudo chmod 600 /etc/secrets/cloudfront-private-key.pem
sudo chown app-user:app-group /etc/secrets/cloudfront-private-key.pem

# Store public key in Terraform
# (will be uploaded to CloudFront via Terraform)
cp cloudfront-public-key.pem infrastructure/terraform/keys/
chmod 644 infrastructure/terraform/keys/cloudfront-public-key.pem
```

## Terraform Key Management

### 1. Update Terraform Configuration

The `cloudfront.tf` file handles key pair creation:

```hcl
# Creates CloudFront public key for signing
resource "aws_cloudfront_public_key" "media_signing" {
  name            = "${var.project_name}-media-key"
  comment         = "Public key for signing media file URLs"
  encoded_key     = file("${path.module}/keys/cloudfront-public-key.pem")
}

# Creates key group for use in distributions
resource "aws_cloudfront_key_group" "media_signing" {
  name    = "${var.project_name}-media-keys"
  comment = "Key group for signing media file URLs"
  items   = [aws_cloudfront_public_key.media_signing.id]
}
```

### 2. Get Key IDs After Terraform Apply

```bash
cd infrastructure/terraform

# Capture outputs
terraform output -json > ../cdn/cloudfront-outputs.json

# Extract key IDs
export CLOUDFRONT_PUBLIC_KEY_ID=$(jq -r '.cloudfront_public_key_id.value' ../cdn/cloudfront-outputs.json)
export CLOUDFRONT_KEY_GROUP_ID=$(jq -r '.cloudfront_key_group_id.value' ../cdn/cloudfront-outputs.json)

echo "Key IDs:"
echo "  Public Key ID: $CLOUDFRONT_PUBLIC_KEY_ID"
echo "  Key Group ID: $CLOUDFRONT_KEY_GROUP_ID"
```

### 3. Update Environment Variables

```bash
# Add to .env
cat >> .env << EOF

# CloudFront Keys
CLOUDFRONT_PUBLIC_KEY_ID=$CLOUDFRONT_PUBLIC_KEY_ID
CLOUDFRONT_PRIVATE_KEY_PATH=/etc/secrets/cloudfront-private-key.pem
EOF
```

## Key Rotation

### Why Rotate Keys?

- Security best practice (annual)
- Compromise mitigation
- Multiple key versions support

### How to Rotate

1. **Generate new key pair**:
   ```bash
   openssl genrsa -out cloudfront-private-key-new.pem 2048
   openssl rsa -in cloudfront-private-key-new.pem -pubout -out cloudfront-public-key-new.pem
   ```

2. **Update Terraform**:
   ```bash
   # Copy new public key
   cp cloudfront-public-key-new.pem infrastructure/terraform/keys/cloudfront-public-key.pem

   # Apply changes
   cd infrastructure/terraform
   terraform plan
   terraform apply
   ```

3. **Gradual Migration**:
   - Deploy new public key to CloudFront
   - Update private key on app servers gradually
   - Monitor for signature failures
   - Keep old key active for 30 days

4. **Update Private Key**:
   ```bash
   sudo cp cloudfront-private-key-new.pem /etc/secrets/cloudfront-private-key.pem
   sudo chown app-user:app-group /etc/secrets/cloudfront-private-key.pem
   sudo chmod 600 /etc/secrets/cloudfront-private-key.pem

   # Restart application
   systemctl restart thebot-backend
   ```

## Testing Key Setup

### 1. Test Signing in Python

```python
# Django shell
python manage.py shell
```

```python
from config.cdn_settings import cdn_config
from datetime import datetime, timedelta

# Test URL signing
test_url = "https://d123456.cloudfront.net/media/test.pdf"

try:
    signed_url = cdn_config.sign_url(test_url, expires_in=3600)
    print("✓ URL signed successfully")
    print(f"URL: {signed_url}")
except Exception as e:
    print(f"✗ Signing failed: {e}")
```

### 2. Test URL Expiration

```python
from config.cdn_settings import cdn_config
import time

# Create URL that expires immediately
test_url = "https://d123456.cloudfront.net/media/test.pdf"
signed_url = cdn_config.sign_url(test_url, expires_in=1)

print(f"Signed URL: {signed_url}")
print("Waiting 2 seconds for URL to expire...")
time.sleep(2)

# Try to access (should fail after 2 seconds)
import requests
response = requests.get(signed_url)
print(f"Response: {response.status_code}")  # Should be 403 Forbidden
```

### 3. Test with curl

```bash
# Get signed URL from application
SIGNED_URL=$(python manage.py shell << 'EOF'
from config.cdn_settings import cdn_config
print(cdn_config.sign_url("https://d123456.cloudfront.net/media/test.pdf"))
EOF
)

# Test with curl
curl -i "$SIGNED_URL"  # Should return 200 with file content
```

## Troubleshooting

### Issue: "Private key not found"

```
ERROR: CloudFront private key not found: /etc/secrets/cloudfront-private-key.pem
```

**Solution**:
```bash
# Verify key exists
ls -la /etc/secrets/cloudfront-private-key.pem

# If missing, restore from backup
cp backup/cloudfront-private-key.pem /etc/secrets/
sudo chown app-user /etc/secrets/cloudfront-private-key.pem
sudo chmod 600 /etc/secrets/cloudfront-private-key.pem

# Restart application
systemctl restart thebot-backend
```

### Issue: "Invalid key format"

```
ValueError: Could not deserialize key data.
```

**Solution**:
```bash
# Check key format
openssl rsa -in /etc/secrets/cloudfront-private-key.pem -check

# If corrupt, restore from backup or regenerate
openssl genrsa -out /etc/secrets/cloudfront-private-key.pem 2048
chmod 600 /etc/secrets/cloudfront-private-key.pem
```

### Issue: "Signature verification failed"

**Cause**: Public/private key mismatch

**Solution**:
```bash
# Verify keys match
openssl rsa -in cloudfront-private-key.pem -pubout > test-public.pem
diff test-public.pem cloudfront-public-key.pem

# If different, regenerate both:
openssl genrsa -out cloudfront-private-key.pem 2048
openssl rsa -in cloudfront-private-key.pem -pubout -out cloudfront-public-key.pem
```

### Issue: "Key pair not found in CloudFront"

```
RuntimeError: CLOUDFRONT_PUBLIC_KEY_ID not set
```

**Solution**:
```bash
# Ensure Terraform applied successfully
cd infrastructure/terraform
terraform output cloudfront_public_key_id

# If empty, apply terraform
terraform apply

# Get outputs
terraform output -json > outputs.json
export CLOUDFRONT_PUBLIC_KEY_ID=$(jq -r '.cloudfront_public_key_id.value' outputs.json)

# Update .env
echo "CLOUDFRONT_PUBLIC_KEY_ID=$CLOUDFRONT_PUBLIC_KEY_ID" >> .env
```

## Key Management Best Practices

1. **Secure Storage**
   - Store private key in `/etc/secrets/` with restricted permissions
   - Use secrets management (AWS Secrets Manager, HashiCorp Vault)
   - Encrypt at rest and in transit

2. **Access Control**
   - Only application process can read private key
   - Use separate service account for app
   - Log all key access

3. **Backup & Recovery**
   - Backup keys to secure location
   - Test recovery process
   - Keep multiple copies in different locations

4. **Monitoring**
   - Log all signed URL generations
   - Monitor for failed signatures
   - Alert on unusual activity

5. **Rotation**
   - Rotate annually or after compromise
   - Support multiple key versions temporarily
   - Test new keys before retiring old ones

## Key Expiration and Renewal

### Terraform Manages Key Lifecycle

```hcl
# aws_cloudfront_public_key
# - No expiration by default
# - Can be disabled and deleted
# - Recommend retiring after 1 year
```

### When to Retire Keys

- Annual security rotation
- After compromise detection
- When switching signing methods
- End of key lifecycle

### Retire Old Key

```bash
cd infrastructure/terraform

# Remove key from terraform
# Edit cloudfront.tf, comment out old key resource

# Apply changes
terraform apply

# Verify new key is active
terraform output cloudfront_public_key_id
```

## References

- [AWS CloudFront Signed URLs Documentation](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/PrivateContent.html)
- [OpenSSL RSA Key Generation](https://www.openssl.org/docs/man1.1.1/man1/genrsa.html)
- [Django Cryptography](https://cryptography.io/)
- [Terraform AWS CloudFront Key Pair](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudfront_public_key)
