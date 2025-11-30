import re
import logging
from rest_framework import serializers
from .models import Application

logger = logging.getLogger(__name__)


class ApplicationSerializer(serializers.ModelSerializer):
    """
    Serializer for applications
    """
    full_name = serializers.ReadOnlyField()
    parent_full_name = serializers.ReadOnlyField()
    
    class Meta:
        model = Application
        fields = [
            'id', 'first_name', 'last_name', 'full_name', 'email', 'phone', 'telegram_id',
            'applicant_type', 'status', 'tracking_token', 'grade', 'subject', 
            'experience', 'motivation', 'parent_first_name', 'parent_last_name', 
            'parent_full_name', 'parent_email', 'parent_phone', 'parent_telegram_id',
            'created_at', 'processed_at', 'processed_by', 'notes'
        ]
        read_only_fields = [
            'id', 'tracking_token', 'created_at', 'processed_at', 'processed_by',
            'generated_username', 'generated_password', 'parent_username', 'parent_password'
        ]


class ApplicationCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating applications
    """
    class Meta:
        model = Application
        fields = [
            'first_name', 'last_name', 'email', 'phone', 'telegram_id',
            'applicant_type', 'grade', 'subject', 'experience', 'motivation',
            'parent_first_name', 'parent_last_name', 'parent_email',
            'parent_phone', 'parent_telegram_id'
        ]

    def validate_email(self, value):
        """
        Validate email is unique across applications
        """
        if not value:
            raise serializers.ValidationError("Email is required")

        if Application.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered for an application")

        return value

    def validate_phone(self, value):
        """
        Validate phone number format (allows spaces, hyphens, parentheses)
        """
        if not value:
            raise serializers.ValidationError("Phone number is required")

        # Clean phone number: remove spaces, hyphens, parentheses
        cleaned_phone = value.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')

        # Simple phone validation: must have at least 5 digits and start with 1-9
        phone_pattern = r'^[\+]?[1-9][\d]{4,15}$'
        if not re.match(phone_pattern, cleaned_phone):
            raise serializers.ValidationError(
                "Invalid phone number format. Use format like +79999999999 or 89999999999"
            )

        return value
    
    def validate_grade(self, value):
        """
        Validate grade for student applications
        """
        if value and (not value.isdigit() or int(value) < 1 or int(value) > 11):
            raise serializers.ValidationError("Grade must be between 1 and 11")
        return value
    
    def validate(self, attrs):
        """
        Cross-field validation with role-specific requirements
        """
        applicant_type = attrs.get('applicant_type')

        # Validate required fields based on applicant type
        if applicant_type == Application.ApplicantType.STUDENT:
            if not attrs.get('grade'):
                raise serializers.ValidationError({
                    'grade': 'Grade is required for student applications'
                })
            # For student applications, parent information is required
            required_parent_fields = ['parent_first_name', 'parent_last_name', 'parent_email', 'parent_phone']
            for field in required_parent_fields:
                if not attrs.get(field):
                    raise serializers.ValidationError({
                        field: f'{field.replace("_", " ").title()} is required for student applications'
                    })
            # Note: motivation is optional for students
            logger.debug("Student application validated successfully")

        elif applicant_type == Application.ApplicantType.TEACHER:
            if not attrs.get('subject'):
                raise serializers.ValidationError({
                    'subject': 'Subject is required for teacher applications'
                })
            if not attrs.get('experience'):
                raise serializers.ValidationError({
                    'experience': 'Experience description is required for teacher applications'
                })
            # Note: motivation is optional for teachers
            logger.debug("Teacher application validated successfully")

        elif applicant_type == Application.ApplicantType.PARENT:
            # Parent applications have minimal requirements
            logger.debug("Parent application validated successfully")

        # telegram_id is optional for all types
        # If provided, it can be with or without @ prefix

        return attrs


class ApplicationStatusUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating application status
    """
    class Meta:
        model = Application
        fields = ['status', 'notes']
    
    def validate_status(self, value):
        """
        Validate status
        """
        valid_statuses = [choice[0] for choice in Application.Status.choices]
        if value not in valid_statuses:
            raise serializers.ValidationError(f"Invalid status. Available: {', '.join(valid_statuses)}")
        return value


class ApplicationTrackingSerializer(serializers.ModelSerializer):
    """
    Serializer for tracking application status (public endpoint)
    """
    class Meta:
        model = Application
        fields = ['tracking_token', 'status', 'created_at', 'processed_at']
        read_only_fields = ['tracking_token', 'status', 'created_at', 'processed_at']
