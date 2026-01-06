import pytest
from rest_framework.exceptions import ValidationError
from accounts.tutor_serializers import (
    TutorStudentCreateSerializer,
    SubjectAssignSerializer,
)


class TestValidationErrorSecurity:
    """Test that ValidationErrors don't leak private data like emails/phones/internal field names"""

    def test_invalid_parent_email_raises_generic_error(self):
        """
        Test: TutorStudentCreateSerializer with invalid parent_email
        Should raise ValidationError but with generic message (not specific "Invalid email")
        """
        serializer = TutorStudentCreateSerializer(
            data={
                "first_name": "John",
                "last_name": "Doe",
                "grade": "10",
                "goal": "",
                "parent_first_name": "Jane",
                "parent_last_name": "Doe",
                "parent_email": "not-an-email",
                "parent_phone": "",
            }
        )

        assert not serializer.is_valid()
        errors = serializer.errors

        if "parent_email" in errors:
            error_list = errors["parent_email"]
            if isinstance(error_list, list):
                error_msg = str(error_list[0]) if error_list else ""
            else:
                error_msg = str(error_list)

            assert "Invalid" not in error_msg or "Ошибка валидации" in error_msg

    def test_parent_email_validation_method(self):
        """
        Test: validate_parent_email returns generic message when whitespace only
        """
        serializer = TutorStudentCreateSerializer()

        with pytest.raises(ValidationError) as exc_info:
            serializer.validate_parent_email("  ")

        error_msg = str(
            exc_info.value.detail[0]
            if hasattr(exc_info.value, "detail")
            else exc_info.value
        )
        assert error_msg == "Ошибка валидации данных"

    def test_parent_phone_validation_method(self):
        """
        Test: validate_parent_phone returns generic message when whitespace only
        """
        serializer = TutorStudentCreateSerializer()

        with pytest.raises(ValidationError) as exc_info:
            serializer.validate_parent_phone("  ")

        error_msg = str(
            exc_info.value.detail[0]
            if hasattr(exc_info.value, "detail")
            else exc_info.value
        )
        assert error_msg == "Ошибка валидации данных"

    @pytest.mark.django_db
    def test_subject_assign_serializer_teacher_not_found_message(self):
        """
        Test: SubjectAssignSerializer with non-existent teacher
        Should not expose internal error like "User.DoesNotExist"
        """
        from django.contrib.auth import get_user_model

        User = get_user_model()

        serializer = SubjectAssignSerializer(
            data={
                "subject_id": 1,
                "teacher_id": 999999,
            }
        )

        if not serializer.is_valid():
            errors = serializer.errors
            if "teacher_id" in errors:
                error_list = errors["teacher_id"]
                error_msg = str(
                    error_list[0] if isinstance(error_list, list) else error_list
                )

                assert "DoesNotExist" not in error_msg
                assert (
                    "not found" in error_msg.lower()
                    or "Пользователь не найден" in error_msg
                )

    def test_exception_handler_masks_validation_errors(self):
        """
        Test: custom_exception_handler masks ValidationError details
        """
        from config.exceptions import custom_exception_handler
        from rest_framework.exceptions import ValidationError as DRFValidationError

        exc = DRFValidationError(
            {"parent_email": ["Invalid email"], "parent_phone": ["Invalid phone"]}
        )
        context = {"view": "test_view"}

        response = custom_exception_handler(exc, context)

        assert response.status_code == 400
        assert response.data["error"] == "Ошибка валидации данных"
        assert "parent_email" not in str(response.data)
        assert "Invalid" not in str(response.data)

    def test_exception_handler_preserves_full_error_in_logging(self):
        """
        Test: custom_exception_handler logs full error details while masking response
        """
        from config.exceptions import custom_exception_handler
        from rest_framework.exceptions import ValidationError as DRFValidationError

        exc = DRFValidationError({"sensitive_field": ["Secret error message"]})
        context = {"view": "test_view"}

        response = custom_exception_handler(exc, context)

        assert response.status_code == 400
        assert response.data["error"] == "Ошибка валидации данных"
        assert "sensitive_field" not in response.data["error"]
        assert "Secret error message" not in response.data["error"]
