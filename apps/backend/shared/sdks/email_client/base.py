from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class EmailMessage:
    """Email message data structure"""

    subject: str
    body: str
    receiver_email: str
    sender_email: Optional[str] = None
    html_body: Optional[str] = None
    attachments: Optional[List[str]] = None


@dataclass
class BulkEmailMessage:
    """Bulk email message data structure"""

    subject: str
    body: str
    receiver_emails: List[str]
    sender_email: Optional[str] = None
    html_body: Optional[str] = None
    attachments: Optional[List[str]] = None


class EmailClientBase(ABC):
    """Base class for email clients"""

    @abstractmethod
    def send_email(self, message: EmailMessage) -> bool:
        """Send a single email"""
        pass

    @abstractmethod
    def send_bulk_email(self, message: BulkEmailMessage) -> Dict[str, bool]:
        """Send bulk emails, returns dict with email -> success status"""
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """Test email service connection"""
        pass
