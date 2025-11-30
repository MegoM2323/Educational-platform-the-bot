from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.db import IntegrityError
from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404
import logging

from .models import Application
from .serializers import (
    ApplicationSerializer, 
    ApplicationCreateSerializer, 
    ApplicationStatusUpdateSerializer,
    ApplicationTrackingSerializer
)
from .telegram_service import telegram_service
from .application_service import application_service
from core.transaction_utils import (
    TransactionType, 
    transaction_manager, 
    ensure_data_integrity,
    log_critical_operation
)

logger = logging.getLogger(__name__)


class ApplicationSubmitView(generics.CreateAPIView):
    """
    Submit new application
    """
    queryset = Application.objects.all()
    serializer_class = ApplicationCreateSerializer
    permission_classes = [AllowAny]  # Allow creating applications without authentication
    
    def perform_create(self, serializer):
        """
        Creates application and sends notification via Telegram.
        Application ALWAYS created, Telegram errors don't block creation.
        """
        def create_application_operation():
            # Create application (validation already done by serializer)
            application = serializer.save()
            logger.info(f"Application saved: id={application.id}, email={application.email}, type={application.applicant_type}")

            # Send notification via Telegram (non-critical operation)
            message_id = None
            telegram_sent = False

            try:
                # Check if Telegram is configured
                if not telegram_service.bot_token:
                    logger.warning(f"Telegram bot token not configured, skipping notification for application {application.id}")
                else:
                    message_id = telegram_service.send_application_notification(application)
                    if message_id:
                        application.telegram_message_id = message_id
                        application.save(update_fields=['telegram_message_id'])
                        telegram_sent = True
                        logger.info(f"Telegram notification sent for application {application.id}, message_id={message_id}")

                        # Send detailed log to log channel
                        try:
                            log_message = (
                                f"🧾 <b>Лог: создана заявка</b>\n\n"
                                f"🆔 <b>ID:</b> #{application.id}\n"
                                f"👤 <b>ФИО:</b> {application.first_name} {application.last_name}\n"
                                f"📧 <b>Email:</b> {application.email}\n"
                                f"📞 <b>Телефон:</b> {application.phone}\n"
                                f"🎭 <b>Тип:</b> {application.get_applicant_type_display()}\n"
                                f"🕒 <b>Время:</b> {timezone.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
                                f"🔗 <b>Tracking:</b> {application.tracking_token}"
                            )
                            telegram_service.send_log(log_message)
                        except Exception as log_err:
                            logger.warning(f"Failed to send detailed log to Telegram: {log_err}")
                    else:
                        logger.warning(f"Telegram notification returned None for application {application.id}")

            except Exception as e:
                logger.error(f"Error sending Telegram notification for app {application.id}: {str(e)}", exc_info=True)
                # Don't interrupt application creation due to Telegram error

            # Always log the operation (regardless of Telegram success)
            log_critical_operation(
                "application_created",
                user_id=None,
                details={
                    'application_id': application.id,
                    'telegram_sent': telegram_sent,
                    'telegram_message_id': message_id
                },
                success=True
            )

            return application

        # Use transaction manager for critical operation
        result = transaction_manager.execute_with_rollback(
            create_application_operation,
            TransactionType.APPLICATION_SUBMISSION,
            "create_application",
            user_id=None
        )

        if not result.success:
            logger.error(f"Error creating application (transaction failed): {result.error}")
            raise Exception(result.error)
    
    def create(self, request, *args, **kwargs):
        """
        Override create to return tracking token with detailed logging
        """
        logger.info(f"ApplicationSubmitView.create() called with data keys: {list(request.data.keys())}")

        try:
            # Log incoming data (sanitized, without sensitive fields)
            safe_data = {k: v for k, v in request.data.items() if k not in ['password', 'token']}
            logger.debug(f"Application submission request: {safe_data}")

            # Validate serializer
            serializer = self.get_serializer(data=request.data)
            if not serializer.is_valid():
                logger.warning(f"Validation errors for application: {serializer.errors}")
                raise ValidationError(serializer.errors)

            logger.debug(f"Validated application data for {serializer.validated_data.get('applicant_type')} applicant")

            # Perform creation with transaction handling
            self.perform_create(serializer)

            # Ensure tracking_token is set
            tracking_token = str(serializer.instance.tracking_token)
            logger.info(f"Application created successfully with tracking_token: {tracking_token}, id: {serializer.instance.id}")

            headers = self.get_success_headers(serializer.data)

            # Build response with tracking token
            response_data = serializer.data.copy()
            response_data['tracking_token'] = tracking_token

            return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)

        except ValidationError as e:
            # Handle validation errors with detailed logging
            logger.warning(f"Validation error creating application: {e.detail}")
            return Response(
                {'errors': e.detail, 'error': 'Validation failed'},
                status=status.HTTP_400_BAD_REQUEST
            )

        except IntegrityError as e:
            # Handle database integrity errors (e.g., duplicate email)
            logger.warning(f"Database integrity error creating application: {str(e)}")
            if 'email' in str(e).lower():
                return Response(
                    {'errors': {'email': ['Email already registered']}},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(
                {'error': 'Database integrity error', 'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            logger.error(f"Unexpected error creating application: {str(e)}", exc_info=True)

            # Try to return tracking_token if application was created before error
            error_response = {
                'error': 'Failed to process application',
                'detail': str(e)
            }

            # Attempt to get the created application instance from serializer
            if hasattr(self, '_wrapped') and hasattr(self._wrapped, 'instance'):
                tracking_token = getattr(self._wrapped.instance, 'tracking_token', None)
                if tracking_token:
                    error_response['tracking_token'] = str(tracking_token)

            return Response(error_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ApplicationListView(generics.ListAPIView):
    """
    List applications (admin only)
    """
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        """
        Filter applications by status
        """
        queryset = super().get_queryset()
        status_filter = self.request.query_params.get('status')
        applicant_type_filter = self.request.query_params.get('applicant_type')
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        if applicant_type_filter:
            queryset = queryset.filter(applicant_type=applicant_type_filter)
        
        return queryset.order_by('-created_at')


class ApplicationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Application details, update and delete (admin only)
    """
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer
    permission_classes = [IsAdminUser]


class ApplicationApproveView(generics.UpdateAPIView):
    """
    Approve application and create user accounts
    """
    queryset = Application.objects.all()
    serializer_class = ApplicationStatusUpdateSerializer
    permission_classes = [IsAdminUser]
    
    def perform_update(self, serializer):
        """
        Approves application, creates user accounts, and sends credentials via Telegram
        """
        application = self.get_object()
        
        def approve_application_operation():
            # Use ApplicationService to approve application and create accounts
            success = application_service.approve_application(application, self.request.user)
            
            if not success:
                raise Exception("Failed to approve application and create user accounts")
            
            log_critical_operation(
                "application_approved",
                user_id=self.request.user.id,
                details={
                    'application_id': application.id,
                    'approved_by': self.request.user.username,
                    'applicant_type': application.applicant_type
                },
                success=True
            )
            
            return success
        
        # Use transaction manager for critical operation
        result = transaction_manager.execute_with_rollback(
            approve_application_operation,
            TransactionType.APPLICATION_APPROVAL,
            "approve_application",
            user_id=self.request.user.id,
            metadata={'application_id': application.id}
        )
        
        if not result.success:
            logger.error(f"Error approving application: {result.error}")
            raise Exception(result.error)


class ApplicationRejectView(generics.UpdateAPIView):
    """
    Reject application
    """
    queryset = Application.objects.all()
    serializer_class = ApplicationStatusUpdateSerializer
    permission_classes = [IsAdminUser]
    
    def perform_update(self, serializer):
        """
        Rejects application and sends notification via Telegram
        """
        application = self.get_object()
        reason = serializer.validated_data.get('notes', '')
        
        try:
            # Use ApplicationService to reject application
            success = application_service.reject_application(application, self.request.user, reason)
            
            if not success:
                raise Exception("Failed to reject application")
                
            logger.info(f"Application #{application.id} successfully rejected by {self.request.user}")
                
        except Exception as e:
            logger.error(f"Error rejecting application: {e}")
            raise


@api_view(['GET'])
@permission_classes([AllowAny])
def application_status(request, token):
    """
    Check application status by tracking token (public endpoint)
    """
    try:
        application = get_object_or_404(Application, tracking_token=token)
        serializer = ApplicationTrackingSerializer(application)
        return Response(serializer.data)
    except Exception as e:
        logger.error(f"Error retrieving application status: {e}")
        return Response(
            {'error': 'Application not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([IsAdminUser])
def application_statistics(request):
    """
    Application statistics (admin only)
    """
    try:
        total_applications = Application.objects.count()
        pending_applications = Application.objects.filter(status=Application.Status.PENDING).count()
        approved_applications = Application.objects.filter(status=Application.Status.APPROVED).count()
        rejected_applications = Application.objects.filter(status=Application.Status.REJECTED).count()
        
        # Applications by type
        student_applications = Application.objects.filter(applicant_type=Application.ApplicantType.STUDENT).count()
        teacher_applications = Application.objects.filter(applicant_type=Application.ApplicantType.TEACHER).count()
        parent_applications = Application.objects.filter(applicant_type=Application.ApplicantType.PARENT).count()
        
        # Applications in the last 7 days
        from datetime import timedelta
        week_ago = timezone.now() - timedelta(days=7)
        recent_applications = Application.objects.filter(created_at__gte=week_ago).count()
        
        statistics = {
            'total': total_applications,
            'pending': pending_applications,
            'approved': approved_applications,
            'rejected': rejected_applications,
            'by_type': {
                'student': student_applications,
                'teacher': teacher_applications,
                'parent': parent_applications
            },
            'recent_week': recent_applications
        }
        
        return Response(statistics)
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return Response(
            {'error': 'Error getting statistics'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAdminUser])
def test_telegram_connection(request):
    """
    Test Telegram connection (admin only)
    """
    try:
        is_connected = telegram_service.test_connection()
        
        if is_connected:
            return Response({
                'status': 'success',
                'message': 'Telegram connection successful'
            })
        else:
            return Response({
                'status': 'error',
                'message': 'Failed to connect to Telegram'
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Error testing Telegram: {e}")
        return Response({
            'status': 'error',
            'message': f'Testing error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
