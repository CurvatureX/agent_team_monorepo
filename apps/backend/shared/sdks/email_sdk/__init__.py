"""
Email SDK for workflow automation.

This SDK provides comprehensive email integration including:
- SMTP email sending with authentication
- Email templating and formatting
- Attachment handling
- Multiple email providers support (Gmail, Outlook, custom SMTP)
- HTML and plain text email support
"""

from .client import EmailSDK
from .exceptions import (
    EmailError,
    EmailAuthError,
    EmailSendError,
    EmailValidationError,
    EmailConnectionError,
)
from .models import EmailMessage, EmailAttachment

__version__ = "1.0.0"
__all__ = [
    "EmailSDK",
    "EmailError",
    "EmailAuthError",
    "EmailSendError",
    "EmailValidationError",
    "EmailConnectionError",
    "EmailMessage",
    "EmailAttachment",
]