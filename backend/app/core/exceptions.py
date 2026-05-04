from fastapi import status
from typing import Any, Dict, Optional

class AppBaseException(Exception):
    def __init__(
        self, 
        message: str, 
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: Optional[Any] = None
    ):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(message)

class NotFoundException(AppBaseException):
    def __init__(self, message: str = "Resource not found", detail: Any = None):
        super().__init__(message, status.HTTP_404_NOT_FOUND, detail)

class UnauthorizedException(AppBaseException):
    def __init__(self, message: str = "Unauthorized access", detail: Any = None):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED, detail)

class ForbiddenException(AppBaseException):
    def __init__(self, message: str = "Forbidden access", detail: Any = None):
        super().__init__(message, status.HTTP_403_FORBIDDEN, detail)

class ValidationException(AppBaseException):
    def __init__(self, message: str = "Validation error", detail: Any = None):
        super().__init__(message, status.HTTP_400_BAD_REQUEST, detail)
