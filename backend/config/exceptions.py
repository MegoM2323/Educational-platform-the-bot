import logging
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.views import exception_handler


logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    if isinstance(exc, DRFValidationError):
        logger.error(
            f"ValidationError in {context.get('view', 'unknown')}: {exc.detail}",
            extra={"full_error": exc.detail},
        )

        return Response({"success": False, "error": "Ошибка валидации данных"}, status=400)

    response = exception_handler(exc, context)
    return response
