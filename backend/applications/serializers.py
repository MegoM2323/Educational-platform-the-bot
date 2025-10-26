import re
from rest_framework import serializers
from .models import Application


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
    
    def validate_phone(self, value):
        """
        Validate phone number format
        """
        if not value:
            raise serializers.ValidationError("Phone number is required")
        
        # Simple phone validation
        phone_pattern = r'^[\+]?[1-9][\d]{0,15}$'
        cleaned_phone = value.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        if not re.match(phone_pattern, cleaned_phone):
            raise serializers.ValidationError("Invalid phone number format")
        
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
        Cross-field validation
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
        
        elif applicant_type == Application.ApplicantType.TEACHER:
            if not attrs.get('subject'):
                raise serializers.ValidationError({
                    'subject': 'Subject is required for teacher applications'
                })
            if not attrs.get('experience'):
                raise serializers.ValidationError({
                    'experience': 'Experience description is required for teacher applications'
                })
        
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
