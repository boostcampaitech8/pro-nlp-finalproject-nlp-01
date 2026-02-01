"""
Custom exception classes for consistent error handling across the application.
"""

from fastapi import HTTPException, status


class ResourceNotFoundError(HTTPException):
    """Raised when a requested resource is not found."""
    
    def __init__(self, resource: str, id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} with id {id} not found"
        )


class ProcessingError(HTTPException):
    """Raised when a background processing task fails."""
    
    def __init__(self, message: str, resource: str = None):
        detail = f"Processing failed: {message}"
        if resource:
            detail = f"{resource} processing failed: {message}"
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )


class ValidationError(HTTPException):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, field: str = None):
        detail = message
        if field:
            detail = f"Validation error in '{field}': {message}"
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail
        )


class UnauthorizedError(HTTPException):
    """Raised when user is not authorized to access a resource."""
    
    def __init__(self, message: str = "Not authorized to access this resource"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=message
        )


class DuplicateResourceError(HTTPException):
    """Raised when attempting to create a duplicate resource."""
    
    def __init__(self, resource: str, field: str = None):
        detail = f"{resource} already exists"
        if field:
            detail = f"{resource} with this {field} already exists"
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail
        )


class ExternalServiceError(HTTPException):
    """Raised when an external service (GitHub, Notion, etc.) fails."""
    
    def __init__(self, service: str, message: str):
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{service} service error: {message}"
        )
