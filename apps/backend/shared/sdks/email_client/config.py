import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class EmailConfig:
    """Email configuration settings"""

    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    use_tls: bool = True
    use_ssl: bool = False
    sender_email: Optional[str] = None
    sender_name: Optional[str] = None
    timeout: int = 30

    @classmethod
    def from_env(cls) -> "EmailConfig":
        """Create config from environment variables"""
        return cls(
            smtp_host=os.getenv("SMTP_HOST", "smtp.migadu.com"),
            smtp_port=int(os.getenv("SMTP_PORT", "465")),
            smtp_username=os.getenv("SMTP_USERNAME", ""),
            smtp_password=os.getenv("SMTP_PASSWORD", ""),
            use_tls=os.getenv("SMTP_USE_TLS", "false").lower() == "true",
            use_ssl=os.getenv("SMTP_USE_SSL", "true").lower() == "true",
            sender_email=os.getenv("SMTP_SENDER_EMAIL"),
            sender_name=os.getenv("SMTP_SENDER_NAME"),
            timeout=int(os.getenv("SMTP_TIMEOUT", "30")),
        )

    @classmethod
    def for_migadu(
        cls,
        username: str,
        password: str,
        sender_email: Optional[str] = None,
        sender_name: Optional[str] = None,
        use_starttls: bool = False,
    ) -> "EmailConfig":
        """Create Migadu-specific configuration"""
        if use_starttls:
            # STARTTLS configuration (port 587)
            return cls(
                smtp_host="smtp.migadu.com",
                smtp_port=587,
                smtp_username=username,
                smtp_password=password,
                use_tls=True,
                use_ssl=False,
                sender_email=sender_email or username,
                sender_name=sender_name,
                timeout=30,
            )
        else:
            # SSL configuration (port 465) - recommended
            return cls(
                smtp_host="smtp.migadu.com",
                smtp_port=465,
                smtp_username=username,
                smtp_password=password,
                use_tls=False,
                use_ssl=True,
                sender_email=sender_email or username,
                sender_name=sender_name,
                timeout=30,
            )

    def validate(self) -> None:
        """Validate configuration"""
        if not self.smtp_host:
            raise ValueError("SMTP host is required")
        if not self.smtp_username:
            raise ValueError("SMTP username is required")
        if not self.smtp_password:
            raise ValueError("SMTP password is required")
        if self.smtp_port <= 0:
            raise ValueError("SMTP port must be positive")
        if self.use_tls and self.use_ssl:
            raise ValueError("Cannot use both TLS and SSL simultaneously")
