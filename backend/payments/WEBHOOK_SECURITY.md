# YooKassa Webhook Security Implementation

## Overview

Enhanced YooKassa webhook handler with two-layer security for invoice payment processing.

## Security Layers

### 1. IP Whitelist Verification

**Function:** `verify_yookassa_ip(request)`

**Purpose:** Ensures webhook requests only come from official YooKassa servers

**Implementation:**
```python
# Официальные IP-адреса YooKassa
YOOKASSA_WEBHOOK_IPS = [
    '185.71.76.0/27',
    '185.71.77.0/27',
    '77.75.153.0/25',
    '77.75.156.11',
    '77.75.156.35',
    '77.75.154.128/25',
    '2a02:5180::/32',
]
```

**Source:** [YooKassa API Documentation](https://yookassa.ru/developers/using-api/webhooks#ip)

### 2. HMAC-SHA256 Signature Verification

**Function:** `verify_yookassa_signature(body, signature, secret_key)`

**Purpose:** Cryptographically verifies webhook authenticity using shared secret

**Algorithm:**
1. YooKassa computes HMAC-SHA256 of request body using `YOOKASSA_SECRET_KEY`
2. Signature sent in header: `X-Yookassa-Webhook-Signature`
3. Backend recomputes signature and compares using `hmac.compare_digest()`
4. Constant-time comparison prevents timing attacks

**Example:**
```python
import hmac
import hashlib

body = b'{"type":"payment.succeeded","object":{"id":"123"}}'
secret = "your_secret_key"

expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
is_valid = hmac.compare_digest(expected, webhook_signature)
```

## Webhook Endpoint

**URL:** `POST /yookassa-webhook/`

**Headers Required:**
- `Content-Type: application/json`
- `X-Yookassa-Webhook-Signature: <hmac_sha256_hex>` (recommended)

**Processing Flow:**

```
1. Request arrives
   ↓
2. Check HTTP method (must be POST)
   ↓
3. Verify IP address (whitelist)
   ↓
4. Verify HMAC signature (if present)
   ↓
5. Parse JSON body
   ↓
6. Check event type (payment.succeeded, etc.)
   ↓
7. Find Payment by yookassa_payment_id
   ↓
8. Atomic transaction:
   - Lock Payment record (select_for_update)
   - Check if already processed (idempotency)
   - Detect payment type (invoice vs subject)
   - Update Payment status → SUCCEEDED
   - If invoice: call mark_invoice_paid()
   - If subject: call process_successful_payment()
   ↓
9. Invalidate cache
   ↓
10. Send notifications (Telegram, WebSocket)
   ↓
11. Return HTTP 200 OK
```

## Invoice Payment Handling

**Detection:**
```python
invoice_id = payment.metadata.get('invoice_id')
if invoice_id:
    # This is invoice payment
```

**Processing:**
```python
from payments.services import mark_invoice_paid

# 1. Update Payment status
payment.status = Payment.Status.SUCCEEDED
payment.paid_at = timezone.now()
payment.save()

# 2. Process invoice
invoice = mark_invoice_paid(invoice_id, payment)
# This calls InvoiceService.process_payment() which:
# - Updates Invoice status → PAID
# - Links Payment to Invoice
# - Creates status history record
# - Broadcasts WebSocket event
# - Sends Telegram notification
# - Invalidates cache
```

## Configuration

### Environment Variables

```env
# Required
YOOKASSA_SHOP_ID=<your_shop_id>
YOOKASSA_SECRET_KEY=<your_secret_key>

# Optional (for testing)
YOOKASSA_WEBHOOK_SECRET=<separate_webhook_secret>
```

### YooKassa Dashboard Setup

1. Login to yookassa.ru
2. Go to Settings → Notifications → HTTP notifications
3. Add webhook URL: `https://your-domain.com/yookassa-webhook/`
   - ⚠️ MUST use HTTPS in production
   - ⚠️ Trailing slash is REQUIRED
4. Select events:
   - payment.succeeded ✓
   - payment.canceled ✓
   - payment.failed ✓
   - payment.waiting_for_capture ✓
5. Enable "Подписывать уведомления" (Sign notifications) ✓
6. Save configuration

## Testing

### Manual Test

```bash
# Create invoice in dashboard
# Send invoice to parent
# Parent clicks Pay button
# Parent enters test card: 4111 1111 1111 1111
# Complete payment
# Check logs for webhook processing

# Expected logs:
# - "YooKassa webhook signature verified successfully"
# - "Detected invoice payment: payment_id=X, invoice_id=Y"
# - "Webhook: Invoice payment processed successfully"
# - Invoice status should be PAID
```

### Signature Verification Test

```python
import hmac
import hashlib

def test_signature():
    secret = "test_secret"
    body = b'{"type":"payment.succeeded"}'

    signature = hmac.new(
        secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    # Verify
    from payments.views import verify_yookassa_signature
    assert verify_yookassa_signature(body, signature, secret) == True
    print("✅ Signature verification works")

test_signature()
```

## Security Best Practices

### ✅ Implemented

- [x] IP whitelist verification
- [x] HMAC signature verification
- [x] Constant-time signature comparison
- [x] HTTPS required in production
- [x] Atomic transaction processing
- [x] Idempotency checks
- [x] Database locking (select_for_update)
- [x] Comprehensive error logging

### ⚠️ Recommended (Optional)

- [ ] Make signature verification MANDATORY (currently optional for backward compatibility)
- [ ] Rate limiting per IP address
- [ ] Webhook event replay protection (nonce)
- [ ] Webhook monitoring alerts (if processing fails)

### 🔒 Security Notes

1. **Never log secret keys** - only log first 8 chars of signatures
2. **Always use HTTPS** - YooKassa requires it in production
3. **Validate metadata** - ensure invoice_id exists before processing
4. **Handle duplicates** - webhook may be sent multiple times
5. **Fail gracefully** - return HTTP 200 even if invoice processing fails

## Troubleshooting

### Webhook not received

**Check:**
1. Is URL accessible from internet? (not localhost)
2. Is HTTPS enabled?
3. Is URL correct in YooKassa dashboard?
4. Check nginx/firewall logs

### Signature verification fails

**Check:**
1. Is `YOOKASSA_SECRET_KEY` correct?
2. Did YooKassa enable "Sign notifications"?
3. Check request body encoding (must be UTF-8)
4. Check logs for signature mismatch details

### Invoice not marked as paid

**Check:**
1. Is `invoice_id` present in `payment.metadata`?
2. Does invoice exist in database?
3. Check webhook processing logs
4. Check Payment status (should be SUCCEEDED)
5. Check Invoice status (should be PAID)

## Files Modified

- `backend/payments/views.py`
  - Added `verify_yookassa_signature()` function
  - Enhanced `yookassa_webhook()` with signature verification
  - Updated docstrings with security details

- `backend/payments/services.py`
  - `mark_invoice_paid()` already implemented
  - Calls `InvoiceService.process_payment()`

- `backend/invoices/models.py`
  - Invoice model already has `paid_at` field
  - Payment model has `yookassa_payment_id`

- `docs/INVOICE_DEPLOYMENT.md`
  - Added webhook security documentation
  - Added configuration instructions
  - Added processing flow diagram

## References

- [YooKassa Webhooks Documentation](https://yookassa.ru/developers/using-api/webhooks)
- [YooKassa API Reference](https://yookassa.ru/developers/api)
- [HMAC Wikipedia](https://en.wikipedia.org/wiki/HMAC)
- [Invoice System Documentation](../docs/INVOICE_SYSTEM.md)
