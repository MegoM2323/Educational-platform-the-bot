#!/bin/bash

# Generate SSL Certificates for Production HTTPS
# ============================================================================
# This script generates self-signed certificates for local testing.
# For production, use Let's Encrypt or purchase a proper certificate.
#
# Usage:
#   ./docker/generate-ssl.sh
#   ./docker/generate-ssl.sh your-domain.com
#

DOMAIN="${1:-localhost}"
CERT_DIR="./docker/ssl"
DAYS_VALID=365

echo "Generating SSL certificates for: $DOMAIN"
echo "Certificate directory: $CERT_DIR"
echo "Valid for: $DAYS_VALID days"

# Create ssl directory if not exists
mkdir -p "$CERT_DIR"

# Generate private key (2048-bit RSA)
echo "1. Generating private key..."
openssl genrsa -out "$CERT_DIR/key.pem" 2048

# Generate CSR (Certificate Signing Request)
echo "2. Generating certificate signing request..."
openssl req -new \
    -key "$CERT_DIR/key.pem" \
    -out "$CERT_DIR/csr.pem" \
    -subj "/C=RU/ST=Russia/L=Moscow/O=THE_BOT/OU=IT/CN=$DOMAIN"

# Generate self-signed certificate
echo "3. Generating self-signed certificate..."
openssl x509 -req \
    -days $DAYS_VALID \
    -in "$CERT_DIR/csr.pem" \
    -signkey "$CERT_DIR/key.pem" \
    -out "$CERT_DIR/cert.pem" \
    -extensions v3_req \
    -extfile <(cat /etc/ssl/openssl.cnf <(printf "[v3_req]\nsubjectAltName=$DOMAIN"))

# Generate self-signed cert directly (alternative method)
openssl req -x509 \
    -newkey rsa:2048 \
    -nodes \
    -days $DAYS_VALID \
    -keyout "$CERT_DIR/key.pem" \
    -out "$CERT_DIR/cert.pem" \
    -subj "/C=RU/ST=Russia/L=Moscow/O=THE_BOT/OU=IT/CN=$DOMAIN" \
    2>/dev/null || true

# Create chain file (for OCSP stapling)
echo "4. Creating certificate chain..."
cp "$CERT_DIR/cert.pem" "$CERT_DIR/chain.pem"

# Generate Diffie-Hellman parameters (for perfect forward secrecy)
echo "5. Generating Diffie-Hellman parameters (this may take a while)..."
openssl dhparam -out "$CERT_DIR/dhparam.pem" 2048

# Verify certificate
echo ""
echo "6. Verifying certificate..."
openssl x509 -in "$CERT_DIR/cert.pem" -text -noout | head -10

# Set correct permissions
chmod 644 "$CERT_DIR/cert.pem"
chmod 600 "$CERT_DIR/key.pem"
chmod 644 "$CERT_DIR/chain.pem"
chmod 644 "$CERT_DIR/dhparam.pem"

echo ""
echo "✓ SSL certificates generated successfully!"
echo ""
echo "Files created:"
echo "  - $CERT_DIR/cert.pem       (Certificate)"
echo "  - $CERT_DIR/key.pem        (Private key)"
echo "  - $CERT_DIR/chain.pem      (Certificate chain)"
echo "  - $CERT_DIR/dhparam.pem    (DH parameters)"
echo "  - $CERT_DIR/csr.pem        (CSR - can be deleted)"
echo ""
echo "⚠️  For production, use Let's Encrypt:"
echo "   certbot certonly --standalone -d your-domain.com"
echo "   Then copy from /etc/letsencrypt/live/your-domain.com/"
