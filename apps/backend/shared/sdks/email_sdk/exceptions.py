"""
Exception classes for Email SDK.
"""


class EmailError(Exception):
    """Base exception for Email SDK."""
    pass


class EmailAuthError(EmailError):
    """Raised when email authentication fails."""
    pass


class EmailSendError(EmailError):
    """Raised when email sending fails."""
    pass


class EmailValidationError(EmailError):
    """Raised when email validation fails."""
    pass


class EmailConnectionError(EmailError):
    """Raised when SMTP connection fails."""
    pass