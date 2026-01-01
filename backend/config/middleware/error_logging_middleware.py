import logging
import traceback
import json
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("django.request")


class ErrorLoggingMiddleware(MiddlewareMixin):
    def process_exception(self, request, exception):
        """
        Логирует исключения с полным traceback.
        HTTP 500 ошибки: полный stack trace
        Остальные ошибки: краткая информация
        """
        status_code = getattr(exception, "status_code", 500)

        if status_code == 500:
            logger.error(
                f"Internal Server Error: {request.method} {request.path}",
                exc_info=True,
                extra={
                    "status_code": 500,
                    "request_method": request.method,
                    "request_path": request.path,
                    "request_user": request.user.username
                    if request.user.is_authenticated
                    else "anonymous",
                },
            )
        elif 400 <= status_code < 500:
            logger.warning(
                f"Client Error {status_code}: {request.method} {request.path} - {str(exception)[:100]}",
                extra={
                    "status_code": status_code,
                    "request_method": request.method,
                    "request_path": request.path,
                    "request_user": request.user.username
                    if request.user.is_authenticated
                    else "anonymous",
                },
            )

        return None
