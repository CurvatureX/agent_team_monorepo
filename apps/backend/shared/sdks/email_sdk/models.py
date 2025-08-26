"""
Data models for Email SDK.
"""

import base64
import mimetypes
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


@dataclass
class EmailAttachment:
    """Represents an email attachment."""

    filename: str
    content: Union[bytes, str]
    content_type: Optional[str] = None

    def __post_init__(self):
        """Post-initialize attachment."""
        # Auto-detect content type if not provided
        if not self.content_type:
            self.content_type = mimetypes.guess_type(self.filename)[0] or "application/octet-stream"

        # Ensure content is bytes
        if isinstance(self.content, str):
            self.content = self.content.encode("utf-8")

    @classmethod
    def from_file(cls, file_path: Union[str, Path]) -> "EmailAttachment":
        """Create attachment from file path."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Attachment file not found: {file_path}")

        with open(path, "rb") as f:
            content = f.read()

        return cls(
            filename=path.name, content=content, content_type=mimetypes.guess_type(str(path))[0]
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmailAttachment":
        """Create attachment from dictionary."""
        content = data.get("content", "")

        # Handle base64 encoded content
        if data.get("encoding") == "base64":
            content = base64.b64decode(content)
        elif isinstance(content, str):
            content = content.encode("utf-8")

        return cls(
            filename=data["filename"], content=content, content_type=data.get("content_type")
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "filename": self.filename,
            "content": base64.b64encode(self.content).decode("utf-8"),
            "content_type": self.content_type,
            "encoding": "base64",
        }


@dataclass
class EmailMessage:
    """Represents an email message."""

    to: Union[str, List[str]]
    subject: str
    body: str
    from_email: Optional[str] = None
    cc: Optional[Union[str, List[str]]] = None
    bcc: Optional[Union[str, List[str]]] = None
    reply_to: Optional[str] = None
    html_body: Optional[str] = None
    attachments: Optional[List[EmailAttachment]] = None
    headers: Optional[Dict[str, str]] = None

    def __post_init__(self):
        """Post-initialize email message."""
        # Normalize email lists
        self.to = self._normalize_email_list(self.to)
        self.cc = self._normalize_email_list(self.cc) if self.cc else None
        self.bcc = self._normalize_email_list(self.bcc) if self.bcc else None

        if self.attachments is None:
            self.attachments = []

        if self.headers is None:
            self.headers = {}

    def _normalize_email_list(self, emails: Union[str, List[str]]) -> List[str]:
        """Normalize email addresses to list."""
        if isinstance(emails, str):
            # Split by comma and clean whitespace
            return [email.strip() for email in emails.split(",") if email.strip()]
        return emails

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmailMessage":
        """Create EmailMessage from dictionary."""
        attachments = None
        if data.get("attachments"):
            attachments = [
                EmailAttachment.from_dict(att) if isinstance(att, dict) else att
                for att in data["attachments"]
            ]

        return cls(
            to=data["to"],
            subject=data["subject"],
            body=data["body"],
            from_email=data.get("from_email"),
            cc=data.get("cc"),
            bcc=data.get("bcc"),
            reply_to=data.get("reply_to"),
            html_body=data.get("html_body"),
            attachments=attachments,
            headers=data.get("headers", {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "to": self.to,
            "subject": self.subject,
            "body": self.body,
            "from_email": self.from_email,
            "cc": self.cc,
            "bcc": self.bcc,
            "reply_to": self.reply_to,
            "html_body": self.html_body,
            "headers": self.headers,
        }

        if self.attachments:
            result["attachments"] = [att.to_dict() for att in self.attachments]

        return result

    def add_attachment(self, attachment: Union[EmailAttachment, str, Path]) -> None:
        """Add attachment to email."""
        if isinstance(attachment, (str, Path)):
            attachment = EmailAttachment.from_file(attachment)

        if self.attachments is None:
            self.attachments = []

        self.attachments.append(attachment)

    @property
    def is_html(self) -> bool:
        """Check if email has HTML content."""
        return bool(self.html_body)

    @property
    def has_attachments(self) -> bool:
        """Check if email has attachments."""
        return bool(self.attachments)

    def validate(self) -> None:
        """Validate email message."""
        if not self.to:
            raise ValueError("Email must have at least one recipient")

        if not self.subject:
            raise ValueError("Email must have a subject")

        if not self.body and not self.html_body:
            raise ValueError("Email must have body content")

        # Validate email addresses format (basic validation)
        import re

        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

        def validate_email(email: str) -> bool:
            return re.match(email_pattern, email.strip()) is not None

        # Validate recipient emails
        for email in self.to:
            if not validate_email(email):
                raise ValueError(f"Invalid email address: {email}")

        # Validate CC emails
        if self.cc:
            for email in self.cc:
                if not validate_email(email):
                    raise ValueError(f"Invalid CC email address: {email}")

        # Validate BCC emails
        if self.bcc:
            for email in self.bcc:
                if not validate_email(email):
                    raise ValueError(f"Invalid BCC email address: {email}")

        # Validate sender email
        if self.from_email and not validate_email(self.from_email):
            raise ValueError(f"Invalid from email address: {self.from_email}")

        # Validate reply-to email
        if self.reply_to and not validate_email(self.reply_to):
            raise ValueError(f"Invalid reply-to email address: {self.reply_to}")
