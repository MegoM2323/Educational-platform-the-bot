import logging
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.views import exception_handler


logger = logging.getLogger(__name__)

SENSITIVE_FIELDS = {
    "password",
    "password_confirm",
    "new_password",
    "new_password_confirm",
    "old_password",
    "ssn",
    "credit_card",
    "card_number",
    "cvv",
    "api_key",
    "secret_key",
    "token",
    "private_key",
}


def _filter_sensitive_fields(errors):
    if isinstance(errors, dict):
        filtered = {}
        for field, messages in errors.items():
            if field.lower() not in SENSITIVE_FIELDS:
                filtered[field] = messages
        return filtered
    return errors


def custom_exception_handler(exc, context):
    if isinstance(exc, DRFValidationError):
        logger.error(
            f"ValidationError in {context.get('view', 'unknown')}: {exc.detail}",
            extra={"full_error": exc.detail},
        )

        return Response(
            {"success": False, "error": "Ошибка валидации данных"}, status=400
        )

    response = exception_handler(exc, context)
    return response
