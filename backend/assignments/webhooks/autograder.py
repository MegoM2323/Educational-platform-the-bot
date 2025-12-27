"""
Autograder webhook handler for external auto-grading service integration.

Receives grading results from external service with HMAC signature verification,
applies grades to submissions, and sends notifications to students.
"""

import hmac
import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from django.http import JsonResponse, HttpRequest
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone

from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, throttle_classes, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.throttling import BaseThrottle

from assignments.models import AssignmentSubmission
from assignments.services.autograder import AutograderService
from assignments.webhooks.models import FailedWebhookLog, WebhookSignatureLog

logger = logging.getLogger(__name__)


class WebhookRateThrottle(BaseThrottle):
    """
    Rate limiting for webhook endpoints: 1000 webhooks per IP per hour.
    Uses circuit breaker pattern to prevent DDoS.
    """
    scope = 'webhook'

    def __init__(self):
        self.max_requests = 1000
        self.duration = 3600  # 1 hour in seconds

    def get_cache_key(self, request, view):
        return f'webhook_throttle_{self.get_ident(request)}'

    def get_ident(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def throttle_success(self):
        """Check if request should be throttled"""
        self.history = cache.get(self.key, [])
        self.now = timezone.now()

        # Drop any requests from the history that have now passed the
        # throttle duration
        while self.history and self.history[-1] <= self.now - timedelta(seconds=self.duration):
            self.history.pop()

        if len(self.history) >= self.max_requests:
            return False

        self.history.insert(0, self.now)
        cache.set(self.key, self.history, self.duration)
        return True

    def throttle(self, request, view):
        self.key = self.get_cache_key(request, view)
        return self.throttle_success()


def verify_webhook_signature(
    payload: bytes,
    signature: str,
    secret: Optional[str] = None
) -> bool:
    """
    Verify HMAC-SHA256 signature of webhook payload.

    Args:
        payload: Raw request body bytes
        signature: Signature from X-Autograder-Signature header
        secret: Secret key for HMAC (from settings.AUTOGRADER_WEBHOOK_SECRET)

    Returns:
        True if signature is valid, False otherwise
    """
    if secret is None:
        secret = getattr(settings, 'AUTOGRADER_WEBHOOK_SECRET', 'default-secret')

    # Calculate expected signature
    expected_signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    # Compare signatures using constant-time comparison
    return hmac.compare_digest(signature, expected_signature)


def check_replay_attack(
    submission_id: int,
    timestamp: str,
    max_age_seconds: int = 300
) -> bool:
    """
    Prevent replay attacks by checking timestamp and submission history.

    Args:
        submission_id: ID of the submission being graded
        timestamp: ISO8601 timestamp from webhook payload
        max_age_seconds: Maximum age of webhook (default 5 minutes)

    Returns:
        True if webhook is not a replay, False if it is
    """
    try:
        webhook_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        now = timezone.now()

        # Check if webhook is too old
        if (now - webhook_time).total_seconds() > max_age_seconds:
            logger.warning(
                f"Webhook too old for submission {submission_id}: "
                f"timestamp={timestamp}"
            )
            return False

        # Check if we've already processed this submission recently
        cache_key = f'autograder_webhook_{submission_id}'
        if cache.get(cache_key):
            logger.warning(
                f"Possible replay attack: submission {submission_id} "
                f"already graded recently"
            )
            return False

        # Mark submission as processed
        cache.set(cache_key, True, 600)  # 10 minute window
        return True

    except (ValueError, AttributeError) as e:
        logger.error(f"Invalid timestamp format: {timestamp}, error: {e}")
        return False


@api_view(['POST'])
@throttle_classes([WebhookRateThrottle])
@authentication_classes([])
@permission_classes([AllowAny])
@csrf_exempt
def autograder_webhook(request: HttpRequest) -> Response:
    """
    Webhook endpoint to receive grading results from external auto-grading service.

    POST /api/webhooks/autograder/

    Headers:
        X-Autograder-Signature: HMAC-SHA256 signature of request body
        Content-Type: application/json

    Payload:
        {
            "submission_id": 123,
            "score": 85,
            "max_score": 100,
            "feedback": "2 tests passed, 1 failed",
            "timestamp": "2025-12-27T10:00:00Z"
        }

    Returns:
        202 Accepted - Webhook queued for processing (will retry on failure)
        400 Bad Request - Invalid payload format
        401 Unauthorized - Invalid signature
        404 Not Found - Submission not found
        409 Conflict - Replay attack detected
        429 Too Many Requests - Rate limit exceeded
        500 Internal Server Error - Processing failed (will retry)
    """
    try:
        # Get raw body for signature verification
        raw_body = request.body

        # Verify HMAC signature
        signature = request.META.get('HTTP_X_AUTOGRADER_SIGNATURE', '')
        if not signature:
            logger.warning("Missing X-Autograder-Signature header")
            return Response(
                {'error': 'Missing X-Autograder-Signature header'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not verify_webhook_signature(raw_body, signature):
            logger.warning(f"Invalid webhook signature: {signature}")
            return Response(
                {'error': 'Invalid signature'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Parse payload
        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON payload: {e}")
            return Response(
                {'error': 'Invalid JSON payload'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate required fields
        required_fields = ['submission_id', 'score', 'max_score', 'feedback', 'timestamp']
        missing_fields = [f for f in required_fields if f not in payload]
        if missing_fields:
            logger.error(f"Missing required fields: {missing_fields}")
            return Response(
                {'error': f'Missing required fields: {missing_fields}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check for replay attacks
        if not check_replay_attack(
            payload['submission_id'],
            payload['timestamp']
        ):
            return Response(
                {'error': 'Replay attack detected'},
                status=status.HTTP_409_CONFLICT
            )

        # Log signature verification
        WebhookSignatureLog.objects.create(
            submission_id=payload['submission_id'],
            signature=signature,
            is_valid=True,
            remote_ip=get_client_ip(request)
        )

        # Process webhook asynchronously with retry mechanism
        service = AutograderService()
        result = service.process_webhook(payload, request)

        # Return 202 Accepted - processing in progress
        return Response(
            {
                'status': 'accepted',
                'message': 'Webhook received and queued for processing',
                'submission_id': payload['submission_id']
            },
            status=status.HTTP_202_ACCEPTED
        )

    except AssignmentSubmission.DoesNotExist:
        logger.warning(
            f"Submission not found: {payload.get('submission_id')}"
        )
        return Response(
            {'error': 'Submission not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    except Exception as e:
        logger.exception(f"Webhook processing failed: {e}")

        # Log failed webhook
        try:
            payload = json.loads(request.body)
            FailedWebhookLog.objects.create(
                submission_id=payload.get('submission_id'),
                payload=payload,
                error_message=str(e),
                remote_ip=get_client_ip(request),
                retry_count=0
            )
        except Exception as log_error:
            logger.error(f"Failed to log webhook error: {log_error}")

        # Return 500 - will be retried
        return Response(
            {'error': 'Internal server error - will retry'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def get_client_ip(request: HttpRequest) -> str:
    """
    Get client IP address from request, handling proxies.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
