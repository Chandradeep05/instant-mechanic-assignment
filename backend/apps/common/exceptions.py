"""
Custom exception classes and DRF exception handler for standardized error contracts.
"""
import logging
from django.conf import settings
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import APIException

logger = logging.getLogger(__name__)

class LiveOpsException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = 'BAD_REQUEST'
    default_detail = 'An error occurred during operations processing.'

    def __init__(self, message=None, code=None, details=None):
        if message:
            self.default_detail = message
        if code:
            self.default_code = code
        self.details = details or {}
        super().__init__(detail=self.default_detail, code=self.default_code)

class InvalidStateTransitionError(LiveOpsException):
    status_code = status.HTTP_409_CONFLICT
    default_code = 'INVALID_STATUS_TRANSITION'
    default_detail = 'The requested status transition is not permitted by the state machine.'

class MechanicUnavailableError(LiveOpsException):
    status_code = status.HTTP_409_CONFLICT
    default_code = 'MECHANIC_UNAVAILABLE'
    default_detail = 'The selected mechanic is not available for assignment.'

class BookingTerminalStateError(LiveOpsException):
    status_code = status.HTTP_409_CONFLICT
    default_code = 'BOOKING_IN_TERMINAL_STATE'
    default_detail = 'The booking is already completed or cancelled and cannot be modified.'

def custom_exception_handler(exc, context):
    """
    Standardizes error responses to:
    {
        "error": {
            "code": "ERROR_CODE",
            "message": "Human readable message",
            "details": {...}
        }
    }
    """
    response = exception_handler(exc, context)

    if isinstance(exc, LiveOpsException):
        return Response(
            {
                "error": {
                    "code": exc.default_code,
                    "message": str(exc.detail),
                    "details": exc.details
                }
            },
            status=exc.status_code
        )

    if response is not None:
        code = 'VALIDATION_ERROR' if response.status_code == 400 else (
            'NOT_FOUND' if response.status_code == 404 else (
                'PERMISSION_DENIED' if response.status_code == 403 else 'API_ERROR'
            )
        )
        message = 'Request validation failed' if response.status_code == 400 else 'An error occurred'
        
        details = response.data
        if isinstance(details, dict) and 'detail' in details:
            message = str(details['detail'])

        return Response(
            {
                "error": {
                    "code": code,
                    "message": message,
                    "details": details
                }
            },
            status=response.status_code
        )

    # Unhandled 500 server error: Log full traceback for ops debugging
    logger.error(f"Unhandled internal server error: {exc}", exc_info=True)
    
    details_payload = str(exc) if settings.DEBUG else "An unexpected error occurred. Please contact ops support."

    return Response(
        {
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected internal server error occurred.",
                "details": details_payload
            }
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )
