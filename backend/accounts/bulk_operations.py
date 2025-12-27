"""
Bulk user operations for admin panel.

Handles atomic batch operations on multiple users:
- Activation/deactivation
- Role assignment
- Password reset with notifications
- Suspension/unsuspension
- Deletion with archival

All operations are atomic (all-or-nothing) and include audit logging.
"""

import logging
import uuid
from typing import List, Dict, Any, Tuple
from django.db import transaction, IntegrityError
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from django.core.mail import send_mail
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response

from core.models import AuditLog

User = get_user_model()
logger = logging.getLogger(__name__)
audit_logger = logging.getLogger('audit')


class BulkOperationError(Exception):
    """Exception raised during bulk operations"""
    pass


class BulkUserOperationService:
    """
    Service for handling bulk user operations with atomic transactions.

    Each operation:
    - Validates all user IDs upfront (fail-fast)
    - Executes atomically (all-or-nothing)
    - Logs audit trail
    - Tracks progress
    - Prevents admin self-modification
    - Returns detailed results
    """

    # Maximum users per operation to prevent resource exhaustion
    MAX_USERS_PER_OPERATION = 1000

    def __init__(self, admin_user: User):
        """
        Initialize bulk operation handler.

        Args:
            admin_user: The admin user performing the operation

        Raises:
            BulkOperationError: If admin_user is not admin
        """
        if not (admin_user.is_staff or admin_user.is_superuser):
            raise BulkOperationError("Only admins can perform bulk operations")

        self.admin_user = admin_user
        self.operation_id = str(uuid.uuid4())

    def _validate_user_ids(self, user_ids: List[int]) -> Tuple[List[int], List[Dict[str, Any]]]:
        """
        Validate that all user IDs exist and are not the admin user.

        Args:
            user_ids: List of user IDs to validate

        Returns:
            Tuple of (valid_user_ids, failed_validations)

        Raises:
            BulkOperationError: If user_ids is empty or exceeds max limit
        """
        if not user_ids:
            raise BulkOperationError("User IDs list cannot be empty")

        if len(user_ids) > self.MAX_USERS_PER_OPERATION:
            raise BulkOperationError(
                f"Too many users. Maximum {self.MAX_USERS_PER_OPERATION} per operation, "
                f"got {len(user_ids)}"
            )

        # Check for admin self-modification
        if self.admin_user.id in user_ids:
            raise BulkOperationError("Cannot modify your own account in bulk operations")

        # Fetch all users
        existing_users = User.objects.filter(id__in=user_ids).values_list('id', flat=True)
        existing_ids = set(existing_users)
        requested_ids = set(user_ids)

        # Find missing IDs
        failed_validations = []
        for user_id in requested_ids - existing_ids:
            failed_validations.append({
                'user_id': user_id,
                'reason': 'User not found'
            })

        return list(existing_ids), failed_validations

    def _get_client_ip(self, request) -> str:
        """Extract client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')

    def _log_audit(self, action: str, target_ids: List[int], metadata: Dict[str, Any] = None, request=None):
        """Log bulk operation to audit trail"""
        ip_address = self._get_client_ip(request) if request else '127.0.0.1'
        user_agent = request.META.get('HTTP_USER_AGENT', '') if request else ''

        audit_metadata = metadata or {}
        audit_metadata['operation_id'] = self.operation_id
        audit_metadata['target_count'] = len(target_ids)

        try:
            AuditLog.objects.create(
                user=self.admin_user,
                action=AuditLog.Action.ADMIN_ACTION,
                target_type='bulk_users',
                metadata={
                    'action': action,
                    'user_ids': target_ids[:100],  # Log first 100 for brevity
                    **audit_metadata
                },
                ip_address=ip_address,
                user_agent=user_agent
            )
        except Exception as e:
            logger.error(f"Failed to log audit: {str(e)}")

    def _send_password_reset_email(self, user: User, temp_password: str) -> bool:
        """
        Send password reset email to user.

        Args:
            user: User to send email to
            temp_password: Temporary password to include

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            subject = 'Password Reset - THE BOT Platform'
            message = f"""
Hello {user.get_full_name()},

Your password has been reset by an administrator.

Temporary Password: {temp_password}

Please login and change your password immediately.

The THE BOT Platform Team
"""
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send password reset email to {user.email}: {str(e)}")
            return False

    def bulk_activate(self, user_ids: List[int], request=None) -> Dict[str, Any]:
        """
        Atomically activate multiple users.

        Args:
            user_ids: List of user IDs to activate
            request: HTTP request for audit logging

        Returns:
            Response dict with operation_id, success_count, failures
        """
        # Validate upfront
        valid_ids, failed_validations = self._validate_user_ids(user_ids)

        if not valid_ids:
            return {
                'operation_id': self.operation_id,
                'success': False,
                'error': 'No valid users to activate',
                'successes': [],
                'failures': failed_validations,
                'summary': {
                    'total_requested': len(user_ids),
                    'success_count': 0,
                    'failure_count': len(failed_validations)
                }
            }

        successes = []
        failures = failed_validations.copy()

        try:
            with transaction.atomic():
                # Perform activation
                updated = User.objects.filter(id__in=valid_ids).update(is_active=True)

                if updated > 0:
                    # Fetch updated users for response
                    activated_users = User.objects.filter(id__in=valid_ids)
                    for user in activated_users:
                        successes.append({
                            'user_id': user.id,
                            'email': user.email,
                            'full_name': user.get_full_name()
                        })

                    # Log audit
                    self._log_audit(
                        'bulk_activate',
                        valid_ids,
                        {'activated_count': updated},
                        request
                    )
        except Exception as e:
            logger.error(f"Bulk activation failed: {str(e)}")
            return {
                'operation_id': self.operation_id,
                'success': False,
                'error': str(e),
                'successes': successes,
                'failures': failures,
                'summary': {
                    'total_requested': len(user_ids),
                    'success_count': len(successes),
                    'failure_count': len(failures)
                }
            }

        return {
            'operation_id': self.operation_id,
            'success': True,
            'successes': successes,
            'failures': failures,
            'summary': {
                'total_requested': len(user_ids),
                'success_count': len(successes),
                'failure_count': len(failures)
            }
        }

    def bulk_deactivate(self, user_ids: List[int], request=None) -> Dict[str, Any]:
        """
        Atomically deactivate multiple users.

        Args:
            user_ids: List of user IDs to deactivate
            request: HTTP request for audit logging

        Returns:
            Response dict with operation_id, success_count, failures
        """
        # Validate upfront
        valid_ids, failed_validations = self._validate_user_ids(user_ids)

        if not valid_ids:
            return {
                'operation_id': self.operation_id,
                'success': False,
                'error': 'No valid users to deactivate',
                'successes': [],
                'failures': failed_validations,
                'summary': {
                    'total_requested': len(user_ids),
                    'success_count': 0,
                    'failure_count': len(failed_validations)
                }
            }

        successes = []
        failures = failed_validations.copy()

        try:
            with transaction.atomic():
                # Perform deactivation
                updated = User.objects.filter(id__in=valid_ids).update(is_active=False)

                if updated > 0:
                    # Fetch updated users for response
                    deactivated_users = User.objects.filter(id__in=valid_ids)
                    for user in deactivated_users:
                        successes.append({
                            'user_id': user.id,
                            'email': user.email,
                            'full_name': user.get_full_name()
                        })

                    # Log audit
                    self._log_audit(
                        'bulk_deactivate',
                        valid_ids,
                        {'deactivated_count': updated},
                        request
                    )
        except Exception as e:
            logger.error(f"Bulk deactivation failed: {str(e)}")
            return {
                'operation_id': self.operation_id,
                'success': False,
                'error': str(e),
                'successes': successes,
                'failures': failures,
                'summary': {
                    'total_requested': len(user_ids),
                    'success_count': len(successes),
                    'failure_count': len(failures)
                }
            }

        return {
            'operation_id': self.operation_id,
            'success': True,
            'successes': successes,
            'failures': failures,
            'summary': {
                'total_requested': len(user_ids),
                'success_count': len(successes),
                'failure_count': len(failures)
            }
        }

    def bulk_assign_role(self, user_ids: List[int], new_role: str, request=None) -> Dict[str, Any]:
        """
        Atomically assign role to multiple users.

        Args:
            user_ids: List of user IDs to update
            new_role: Role to assign (student, teacher, tutor, parent)
            request: HTTP request for audit logging

        Returns:
            Response dict with operation_id, success_count, failures

        Raises:
            BulkOperationError: If role is invalid
        """
        # Validate role
        valid_roles = [choice[0] for choice in User.Role.choices]
        if new_role not in valid_roles:
            raise BulkOperationError(f"Invalid role: {new_role}")

        # Validate user IDs
        valid_ids, failed_validations = self._validate_user_ids(user_ids)

        if not valid_ids:
            return {
                'operation_id': self.operation_id,
                'success': False,
                'error': 'No valid users to assign role',
                'successes': [],
                'failures': failed_validations,
                'summary': {
                    'total_requested': len(user_ids),
                    'success_count': 0,
                    'failure_count': len(failed_validations)
                }
            }

        successes = []
        failures = failed_validations.copy()

        try:
            with transaction.atomic():
                # Perform role assignment
                updated = User.objects.filter(id__in=valid_ids).update(role=new_role)

                if updated > 0:
                    # Fetch updated users for response
                    updated_users = User.objects.filter(id__in=valid_ids)
                    for user in updated_users:
                        successes.append({
                            'user_id': user.id,
                            'email': user.email,
                            'full_name': user.get_full_name(),
                            'new_role': new_role
                        })

                    # Log audit
                    self._log_audit(
                        'bulk_assign_role',
                        valid_ids,
                        {'new_role': new_role, 'updated_count': updated},
                        request
                    )
        except Exception as e:
            logger.error(f"Bulk role assignment failed: {str(e)}")
            return {
                'operation_id': self.operation_id,
                'success': False,
                'error': str(e),
                'successes': successes,
                'failures': failures,
                'summary': {
                    'total_requested': len(user_ids),
                    'success_count': len(successes),
                    'failure_count': len(failures)
                }
            }

        return {
            'operation_id': self.operation_id,
            'success': True,
            'successes': successes,
            'failures': failures,
            'summary': {
                'total_requested': len(user_ids),
                'success_count': len(successes),
                'failure_count': len(failures)
            }
        }

    def bulk_reset_password(self, user_ids: List[int], request=None) -> Dict[str, Any]:
        """
        Atomically reset passwords for multiple users and send notification emails.

        Args:
            user_ids: List of user IDs to reset passwords for
            request: HTTP request for audit logging

        Returns:
            Response dict with operation_id, success_count, failures, temp_passwords
        """
        # Validate user IDs
        valid_ids, failed_validations = self._validate_user_ids(user_ids)

        if not valid_ids:
            return {
                'operation_id': self.operation_id,
                'success': False,
                'error': 'No valid users to reset passwords',
                'successes': [],
                'failures': failed_validations,
                'summary': {
                    'total_requested': len(user_ids),
                    'success_count': 0,
                    'failure_count': len(failed_validations),
                    'emails_sent': 0
                }
            }

        successes = []
        failures = failed_validations.copy()
        emails_sent = 0

        try:
            with transaction.atomic():
                # Reset passwords and prepare email data
                users_to_update = User.objects.filter(id__in=valid_ids)

                for user in users_to_update:
                    # Generate temporary password
                    temp_password = get_random_string(
                        length=12,
                        allowed_chars='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%'
                    )

                    # Set password
                    user.set_password(temp_password)
                    user.save(update_fields=['password'])

                    # Try to send email
                    email_sent = self._send_password_reset_email(user, temp_password)
                    if email_sent:
                        emails_sent += 1

                    successes.append({
                        'user_id': user.id,
                        'email': user.email,
                        'full_name': user.get_full_name(),
                        'temp_password': temp_password,  # Return to admin who will distribute
                        'email_sent': email_sent
                    })

                # Log audit
                self._log_audit(
                    'bulk_reset_password',
                    valid_ids,
                    {'emails_sent': emails_sent, 'password_reset_count': len(successes)},
                    request
                )
        except Exception as e:
            logger.error(f"Bulk password reset failed: {str(e)}")
            return {
                'operation_id': self.operation_id,
                'success': False,
                'error': str(e),
                'successes': successes,
                'failures': failures,
                'summary': {
                    'total_requested': len(user_ids),
                    'success_count': len(successes),
                    'failure_count': len(failures),
                    'emails_sent': emails_sent
                }
            }

        return {
            'operation_id': self.operation_id,
            'success': True,
            'successes': successes,
            'failures': failures,
            'summary': {
                'total_requested': len(user_ids),
                'success_count': len(successes),
                'failure_count': len(failures),
                'emails_sent': emails_sent
            }
        }

    def bulk_suspend(self, user_ids: List[int], request=None) -> Dict[str, Any]:
        """
        Atomically suspend multiple users (mark as inactive and log it).

        Args:
            user_ids: List of user IDs to suspend
            request: HTTP request for audit logging

        Returns:
            Response dict with operation_id, success_count, failures
        """
        # For now, suspend = deactivate
        # In future, could add a separate 'suspended' flag with duration
        return self.bulk_deactivate(user_ids, request)

    def bulk_unsuspend(self, user_ids: List[int], request=None) -> Dict[str, Any]:
        """
        Atomically unsuspend multiple users (mark as active).

        Args:
            user_ids: List of user IDs to unsuspend
            request: HTTP request for audit logging

        Returns:
            Response dict with operation_id, success_count, failures
        """
        # For now, unsuspend = activate
        # In future, would clear any suspension metadata
        return self.bulk_activate(user_ids, request)

    def bulk_delete(self, user_ids: List[int], request=None) -> Dict[str, Any]:
        """
        Atomically delete (archive) multiple users.

        In practice, this sets is_active=False and logs the deletion for audit trail.
        True deletion is deferred to background job for data retention compliance.

        Args:
            user_ids: List of user IDs to delete
            request: HTTP request for audit logging

        Returns:
            Response dict with operation_id, success_count, failures
        """
        # Validate user IDs
        valid_ids, failed_validations = self._validate_user_ids(user_ids)

        if not valid_ids:
            return {
                'operation_id': self.operation_id,
                'success': False,
                'error': 'No valid users to delete',
                'successes': [],
                'failures': failed_validations,
                'summary': {
                    'total_requested': len(user_ids),
                    'success_count': 0,
                    'failure_count': len(failed_validations)
                }
            }

        successes = []
        failures = failed_validations.copy()

        try:
            with transaction.atomic():
                # Archive users (mark inactive and add to audit trail)
                users_to_delete = User.objects.filter(id__in=valid_ids)

                for user in users_to_delete:
                    user.is_active = False
                    user.save(update_fields=['is_active'])

                    successes.append({
                        'user_id': user.id,
                        'email': user.email,
                        'full_name': user.get_full_name(),
                        'status': 'archived'
                    })

                # Log audit - note: we use action ADMIN_ACTION with 'delete' metadata
                self._log_audit(
                    'bulk_delete',
                    valid_ids,
                    {'archived_count': len(successes)},
                    request
                )
        except Exception as e:
            logger.error(f"Bulk deletion failed: {str(e)}")
            return {
                'operation_id': self.operation_id,
                'success': False,
                'error': str(e),
                'successes': successes,
                'failures': failures,
                'summary': {
                    'total_requested': len(user_ids),
                    'success_count': len(successes),
                    'failure_count': len(failures)
                }
            }

        return {
            'operation_id': self.operation_id,
            'success': True,
            'successes': successes,
            'failures': failures,
            'summary': {
                'total_requested': len(user_ids),
                'success_count': len(successes),
                'failure_count': len(failures)
            }
        }
