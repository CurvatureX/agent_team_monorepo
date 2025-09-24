"""
Email SDK client implementation.
"""

import os
import smtplib
import ssl
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Optional

from ..base import APIResponse, BaseSDK, OAuth2Config
from .exceptions import (
    EmailAuthError,
    EmailConnectionError,
    EmailError,
    EmailSendError,
    EmailValidationError,
)
from .models import EmailAttachment, EmailMessage


class EmailSDK(BaseSDK):
    """Email SDK client."""

    @property
    def base_url(self) -> str:
        # Email uses SMTP, no HTTP base URL
        return ""

    @property
    def supported_operations(self) -> Dict[str, str]:
        base = {
            "send_email": "Send email message",
            "send_html_email": "Send HTML formatted email",
            "send_template_email": "Send email using template",
            "validate_email": "Validate email address",
            "test_connection": "Test SMTP connection",
        }
        # MCP alias for gmail
        return {**base, "gmail_send_email": base["send_email"]}

    def get_oauth2_config(self) -> OAuth2Config:
        """Get OAuth2 configuration (for Gmail OAuth)."""
        return OAuth2Config(
            client_id=os.getenv("GMAIL_CLIENT_ID", ""),
            client_secret=os.getenv("GMAIL_CLIENT_SECRET", ""),
            auth_url="https://accounts.google.com/o/oauth2/auth",
            token_url="https://oauth2.googleapis.com/token",
            revoke_url="https://oauth2.googleapis.com/revoke",
            scopes=["https://www.googleapis.com/auth/gmail.send"],
            redirect_uri=os.getenv(
                "GMAIL_REDIRECT_URI", "http://localhost:8002/api/v1/oauth2/gmail/callback"
            ),
        )

    def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """Validate email credentials."""
        # For SMTP
        if "smtp_server" in credentials:
            return all(
                [
                    credentials.get("smtp_server"),
                    credentials.get("smtp_port"),
                    credentials.get("username"),
                    credentials.get("password"),
                ]
            )
        # For OAuth2 (Gmail)
        elif "access_token" in credentials:
            return bool(credentials["access_token"])
        # Basic email credentials
        else:
            return all([credentials.get("username"), credentials.get("password")])

    async def call_operation(
        self, operation: str, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> APIResponse:
        """Execute email operation."""
        if not self.validate_credentials(credentials):
            return APIResponse(
                success=False,
                error="Invalid credentials: missing required email configuration",
                provider="email",
                operation=operation,
            )

        if operation not in self.supported_operations:
            return APIResponse(
                success=False,
                error=f"Unsupported operation: {operation}",
                provider="email",
                operation=operation,
            )

        try:
            # Route to specific operation handler
            handler_map = {
                "send_email": self._send_email,
                "send_html_email": self._send_html_email,
                "send_template_email": self._send_template_email,
                "validate_email": self._validate_email,
                "test_connection": self._test_smtp_connection,
            }
            # Normalize Gmail MCP alias
            op = operation
            if op == "gmail_send_email":
                op = "send_email"
            handler = handler_map[op]
            result = await handler(parameters, credentials)

            return APIResponse(success=True, data=result, provider="email", operation=operation)

        except (EmailAuthError, EmailConnectionError) as e:
            return APIResponse(
                success=False,
                error=str(e),
                provider="email",
                operation=operation,
                status_code=401 if isinstance(e, EmailAuthError) else 503,
            )
        except (EmailValidationError, EmailSendError) as e:
            return APIResponse(
                success=False, error=str(e), provider="email", operation=operation, status_code=400
            )
        except Exception as e:
            self.logger.error(f"Email {operation} failed: {str(e)}")
            return APIResponse(success=False, error=str(e), provider="email", operation=operation)

    async def _send_email(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Send email message."""
        # Create email message from parameters
        try:
            email_msg = EmailMessage.from_dict(parameters)
            email_msg.validate()
        except Exception as e:
            raise EmailValidationError(f"Invalid email parameters: {str(e)}")

        # Use from_email from credentials if not provided in message
        if not email_msg.from_email:
            email_msg.from_email = credentials.get("username") or credentials.get("from_email")

        # Send via SMTP
        result = self._send_via_smtp(email_msg, credentials)

        return {
            "message_id": result.get("message_id"),
            "status": "sent",
            "recipients": email_msg.to,
            "subject": email_msg.subject,
        }

    async def _send_html_email(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Send HTML email."""
        # Ensure HTML body is provided
        if "html_body" not in parameters:
            raise EmailValidationError("HTML body is required for HTML email")

        return await self._send_email(parameters, credentials)

    async def _send_template_email(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Send email using template."""
        template = parameters.get("template")
        template_data = parameters.get("template_data", {})

        if not template:
            raise EmailValidationError("Template is required for template email")

        # Simple template rendering (replace {{variable}} with values)
        body = parameters.get("body", "")
        html_body = parameters.get("html_body", "")

        for key, value in template_data.items():
            placeholder = f"{{{{{key}}}}}"
            body = body.replace(placeholder, str(value))
            html_body = html_body.replace(placeholder, str(value))

        # Update parameters with rendered content
        updated_params = parameters.copy()
        updated_params["body"] = body
        if html_body:
            updated_params["html_body"] = html_body

        return await self._send_email(updated_params, credentials)

    async def _validate_email(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Validate email address."""
        email = parameters.get("email")
        if not email:
            raise EmailValidationError("Email address is required for validation")

        try:
            # Basic email validation using EmailMessage
            msg = EmailMessage(to=email, subject="Test", body="Test")
            msg.validate()

            return {"email": email, "valid": True, "format_valid": True}
        except Exception as e:
            return {"email": email, "valid": False, "format_valid": False, "error": str(e)}

    async def _test_smtp_connection(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Test SMTP connection."""
        try:
            smtp_server = credentials.get("smtp_server", "smtp.gmail.com")
            smtp_port = int(credentials.get("smtp_port", 587))
            username = credentials.get("username")
            password = credentials.get("password")

            # Test SMTP connection
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls(context=ssl.create_default_context())
            server.login(username, password)
            server.quit()

            return {
                "connection_valid": True,
                "smtp_server": smtp_server,
                "smtp_port": smtp_port,
                "auth_valid": True,
            }
        except smtplib.SMTPAuthenticationError as e:
            raise EmailAuthError(f"SMTP authentication failed: {str(e)}")
        except Exception as e:
            raise EmailConnectionError(f"SMTP connection failed: {str(e)}")

    async def _test_connection_impl(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        """Test email connection."""
        return await self._test_smtp_connection({}, credentials)

    def _send_via_smtp(
        self, email_msg: EmailMessage, credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Send email via SMTP."""
        try:
            # Get SMTP configuration
            smtp_server = credentials.get("smtp_server", "smtp.gmail.com")
            smtp_port = int(credentials.get("smtp_port", 587))
            username = credentials.get("username")
            password = credentials.get("password")
            use_tls = credentials.get("use_tls", "true").lower() == "true"

            # Create MIME message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = email_msg.subject
            msg["From"] = email_msg.from_email or username
            msg["To"] = ", ".join(email_msg.to)

            if email_msg.cc:
                msg["Cc"] = ", ".join(email_msg.cc)
            if email_msg.reply_to:
                msg["Reply-To"] = email_msg.reply_to

            # Add custom headers
            if email_msg.headers:
                for key, value in email_msg.headers.items():
                    msg[key] = value

            # Add text body
            if email_msg.body:
                text_part = MIMEText(email_msg.body, "plain")
                msg.attach(text_part)

            # Add HTML body
            if email_msg.html_body:
                html_part = MIMEText(email_msg.html_body, "html")
                msg.attach(html_part)

            # Add attachments
            if email_msg.attachments:
                for attachment in email_msg.attachments:
                    att_part = MIMEApplication(attachment.content, Name=attachment.filename)
                    att_part[
                        "Content-Disposition"
                    ] = f'attachment; filename="{attachment.filename}"'
                    if attachment.content_type:
                        att_part.set_type(attachment.content_type)
                    msg.attach(att_part)

            # Connect to SMTP server and send
            server = smtplib.SMTP(smtp_server, smtp_port)

            if use_tls:
                server.starttls(context=ssl.create_default_context())

            if username and password:
                server.login(username, password)

            # Build recipient list
            recipients = email_msg.to.copy()
            if email_msg.cc:
                recipients.extend(email_msg.cc)
            if email_msg.bcc:
                recipients.extend(email_msg.bcc)

            # Send email
            result = server.sendmail(msg["From"], recipients, msg.as_string())
            server.quit()

            # Generate message ID (simplified)
            import uuid

            message_id = str(uuid.uuid4())

            return {
                "message_id": message_id,
                "smtp_result": result,
                "recipients_count": len(recipients),
            }

        except smtplib.SMTPAuthenticationError as e:
            raise EmailAuthError(f"SMTP authentication failed: {str(e)}")
        except smtplib.SMTPException as e:
            raise EmailSendError(f"SMTP error: {str(e)}")
        except Exception as e:
            raise EmailSendError(f"Email sending failed: {str(e)}")
