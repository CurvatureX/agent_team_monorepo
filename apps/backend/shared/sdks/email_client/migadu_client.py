import logging
from typing import Optional

from .config import EmailConfig
from .smtp_client import SMTPEmailClient

logger = logging.getLogger(__name__)


class MigaduEmailClient(SMTPEmailClient):
    """Migadu-specific email client with optimized configuration"""

    def __init__(
        self,
        username: str,
        password: str,
        sender_email: Optional[str] = None,
        sender_name: Optional[str] = None,
        use_starttls: bool = False,
    ):
        """
        Initialize Migadu email client

        Args:
            username: Full email address (e.g., yourname@yourdomain.com)
            password: Email account password
            sender_email: Optional sender email (defaults to username)
            sender_name: Optional sender display name
            use_starttls: Use STARTTLS (port 587) instead of SSL (port 465)
        """
        config = EmailConfig.for_migadu(
            username=username,
            password=password,
            sender_email=sender_email,
            sender_name=sender_name,
            use_starttls=use_starttls,
        )

        super().__init__(config)
        logger.info(
            f"Initialized Migadu client for {username} using {'STARTTLS' if use_starttls else 'SSL'}"
        )

    @classmethod
    def from_env(cls) -> "MigaduEmailClient":
        """Create Migadu client from environment variables"""
        import os

        username = os.getenv("MIGADU_USERNAME") or os.getenv("SMTP_USERNAME", "")
        password = os.getenv("MIGADU_PASSWORD") or os.getenv("SMTP_PASSWORD", "")
        sender_email = os.getenv("MIGADU_SENDER_EMAIL") or os.getenv("SMTP_SENDER_EMAIL")
        sender_name = os.getenv("MIGADU_SENDER_NAME") or os.getenv("SMTP_SENDER_NAME")
        use_starttls = os.getenv("MIGADU_USE_STARTTLS", "false").lower() == "true"

        if not username or not password:
            raise ValueError(
                "MIGADU_USERNAME/SMTP_USERNAME and MIGADU_PASSWORD/SMTP_PASSWORD are required"
            )

        return cls(
            username=username,
            password=password,
            sender_email=sender_email,
            sender_name=sender_name,
            use_starttls=use_starttls,
        )
