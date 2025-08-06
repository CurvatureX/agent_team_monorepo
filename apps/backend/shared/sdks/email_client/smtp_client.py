import logging
import os
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Optional

from .base import BulkEmailMessage, EmailClientBase, EmailMessage
from .config import EmailConfig

logger = logging.getLogger(__name__)


class SMTPEmailClient(EmailClientBase):
    """SMTP email client implementation"""

    def __init__(self, config: EmailConfig):
        self.config = config
        self.config.validate()

    def _create_smtp_connection(self) -> smtplib.SMTP:
        """Create and configure SMTP connection"""
        if self.config.use_ssl:
            smtp = smtplib.SMTP_SSL(
                self.config.smtp_host, self.config.smtp_port, timeout=self.config.timeout
            )
        else:
            smtp = smtplib.SMTP(
                self.config.smtp_host, self.config.smtp_port, timeout=self.config.timeout
            )
            if self.config.use_tls:
                smtp.starttls()

        smtp.login(self.config.smtp_username, self.config.smtp_password)
        return smtp

    def _create_message(
        self,
        subject: str,
        body: str,
        receiver_email: str,
        sender_email: Optional[str] = None,
        html_body: Optional[str] = None,
        attachments: Optional[List[str]] = None,
    ) -> MIMEMultipart:
        """Create email message"""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = sender_email or self.config.sender_email or self.config.smtp_username
        msg["To"] = receiver_email

        if self.config.sender_name:
            msg["From"] = f"{self.config.sender_name} <{msg['From']}>"

        # Add text body
        text_part = MIMEText(body, "plain", "utf-8")
        msg.attach(text_part)

        # Add HTML body if provided
        if html_body:
            html_part = MIMEText(html_body, "html", "utf-8")
            msg.attach(html_part)

        # Add attachments if provided
        if attachments:
            for file_path in attachments:
                if os.path.exists(file_path):
                    with open(file_path, "rb") as attachment:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(attachment.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            "Content-Disposition",
                            f"attachment; filename= {os.path.basename(file_path)}",
                        )
                        msg.attach(part)
                else:
                    logger.warning(f"Attachment file not found: {file_path}")

        return msg

    def send_email(self, message: EmailMessage) -> bool:
        """Send a single email"""
        try:
            smtp = self._create_smtp_connection()

            msg = self._create_message(
                subject=message.subject,
                body=message.body,
                receiver_email=message.receiver_email,
                sender_email=message.sender_email,
                html_body=message.html_body,
                attachments=message.attachments,
            )

            sender = message.sender_email or self.config.sender_email or self.config.smtp_username
            smtp.send_message(msg, from_addr=sender, to_addrs=[message.receiver_email])
            smtp.quit()

            logger.info(f"Email sent successfully to {message.receiver_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {message.receiver_email}: {str(e)}")
            return False

    def send_bulk_email(self, message: BulkEmailMessage) -> Dict[str, bool]:
        """Send bulk emails"""
        results = {}

        try:
            smtp = self._create_smtp_connection()
            sender = message.sender_email or self.config.sender_email or self.config.smtp_username

            for receiver_email in message.receiver_emails:
                try:
                    msg = self._create_message(
                        subject=message.subject,
                        body=message.body,
                        receiver_email=receiver_email,
                        sender_email=message.sender_email,
                        html_body=message.html_body,
                        attachments=message.attachments,
                    )

                    smtp.send_message(msg, from_addr=sender, to_addrs=[receiver_email])
                    results[receiver_email] = True
                    logger.info(f"Bulk email sent successfully to {receiver_email}")

                except Exception as e:
                    results[receiver_email] = False
                    logger.error(f"Failed to send bulk email to {receiver_email}: {str(e)}")

            smtp.quit()

        except Exception as e:
            logger.error(f"Failed to establish SMTP connection for bulk email: {str(e)}")
            # Mark all emails as failed if connection fails
            for email in message.receiver_emails:
                results[email] = False

        return results

    def test_connection(self) -> bool:
        """Test SMTP connection"""
        try:
            smtp = self._create_smtp_connection()
            smtp.quit()
            logger.info("SMTP connection test successful")
            return True
        except Exception as e:
            logger.error(f"SMTP connection test failed: {str(e)}")
            return False
