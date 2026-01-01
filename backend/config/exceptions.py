from rest_framework.response import Response
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    if isinstance(exc, DRFValidationError):
        if isinstance(exc.detail, dict):
            first_key = list(exc.detail.keys())[0]
            error_msg = exc.detail[first_key]
            if isinstance(error_msg, list):
                error_msg = error_msg[0]
            error_msg = str(error_msg)
        elif isinstance(exc.detail, list):
            if len(exc.detail) > 0:
                error_msg = str(exc.detail[0])
            else:
                error_msg = "Validation error"
        else:
            error_msg = str(exc.detail) if exc.detail else "Validation error"

        return Response({"success": False, "error": error_msg}, status=400)

    response = exception_handler(exc, context)
    return response
