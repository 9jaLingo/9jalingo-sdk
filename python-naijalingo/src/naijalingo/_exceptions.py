"""Exceptions for the 9jaLingo SDK."""


class NaijaLingoError(Exception):
    """Base exception for all 9jaLingo SDK errors."""

    def __init__(self, message: str, status_code: int | None = None, response: dict | None = None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(message)


class AuthenticationError(NaijaLingoError):
    """Raised when API key is missing or invalid."""


class RateLimitError(NaijaLingoError):
    """Raised when rate limit is exceeded."""


class NotFoundError(NaijaLingoError):
    """Raised when a requested resource is not found."""


class ServerError(NaijaLingoError):
    """Raised when the API returns a 5xx error."""


class ConnectionError(NaijaLingoError):
    """Raised when unable to connect to the API."""
