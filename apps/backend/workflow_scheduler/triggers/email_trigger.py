import asyncio
import base64
import email
import logging
import re
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

import aioimaplib

from shared.models.execution_new import ExecutionStatus
from shared.models.node_enums import TriggerSubtype
from shared.models.trigger import TriggerStatus
from shared.models.workflow import WorkflowExecutionResponse
from workflow_scheduler.core.config import settings
from workflow_scheduler.triggers.base import BaseTrigger

logger = logging.getLogger(__name__)


class EmailTrigger(BaseTrigger):
    """Email-based trigger using IMAP monitoring"""

    def __init__(self, workflow_id: str, trigger_config: Dict[str, Any]):
        super().__init__(workflow_id, trigger_config)

        self.email_filter = trigger_config.get("email_filter", "")
        self.folder = trigger_config.get("folder", "INBOX")
        self.mark_as_read = trigger_config.get("mark_as_read", True)
        self.attachment_processing = trigger_config.get("attachment_processing", "include")
        self.check_interval = trigger_config.get("check_interval", settings.email_check_interval)

        # IMAP connection settings
        self.imap_server = settings.imap_server
        self.email_user = settings.email_user
        self.email_password = settings.email_password

        # Internal state
        self._monitoring_task: Optional[asyncio.Task] = None
        self._stop_monitoring = False
        self._last_uid = None  # Track last processed email UID

        if not self.email_user or not self.email_password:
            raise ValueError("Email credentials not configured")

    @property
    def trigger_type(self) -> str:
        return TriggerSubtype.EMAIL.value

    async def start(self) -> bool:
        """Start email monitoring"""
        try:
            if not self.enabled:
                logger.info(f"Email trigger for workflow {self.workflow_id} is disabled")
                self.status = TriggerStatus.PAUSED
                return True

            # Test IMAP connection first
            connection_test = await self._test_imap_connection()
            if not connection_test:
                logger.error(f"IMAP connection test failed for workflow {self.workflow_id}")
                self.status = TriggerStatus.ERROR
                return False

            # Start monitoring task
            self._stop_monitoring = False
            self._monitoring_task = asyncio.create_task(self._monitor_emails())

            self.status = TriggerStatus.ACTIVE
            logger.info(f"Email trigger started for workflow {self.workflow_id}")

            return True

        except Exception as e:
            logger.error(
                f"Failed to start email trigger for workflow {self.workflow_id}: {e}",
                exc_info=True,
            )
            self.status = TriggerStatus.ERROR
            return False

    async def stop(self) -> bool:
        """Stop email monitoring"""
        try:
            self._stop_monitoring = True

            if self._monitoring_task and not self._monitoring_task.done():
                self._monitoring_task.cancel()
                try:
                    await self._monitoring_task
                except asyncio.CancelledError:
                    pass

            self.status = TriggerStatus.STOPPED
            logger.info(f"Email trigger stopped for workflow {self.workflow_id}")

            return True

        except Exception as e:
            logger.error(
                f"Failed to stop email trigger for workflow {self.workflow_id}: {e}",
                exc_info=True,
            )
            return False

    async def _test_imap_connection(self) -> bool:
        """Test IMAP connection"""
        try:
            imap_client = aioimaplib.IMAP4_SSL(host=self.imap_server, port=993)
            await imap_client.wait_hello_from_server()

            login_result = await imap_client.login(self.email_user, self.email_password)
            if login_result.result != "OK":
                logger.error(f"IMAP login failed: {login_result}")
                return False

            await imap_client.logout()
            return True

        except Exception as e:
            logger.error(f"IMAP connection test failed: {e}", exc_info=True)
            return False

    async def _monitor_emails(self) -> None:
        """Main email monitoring loop"""
        logger.info(f"Started email monitoring for workflow {self.workflow_id}")

        while not self._stop_monitoring:
            try:
                await self._check_new_emails()
                await asyncio.sleep(self.check_interval)

            except asyncio.CancelledError:
                logger.info(f"Email monitoring cancelled for workflow {self.workflow_id}")
                break

            except Exception as e:
                logger.error(
                    f"Error in email monitoring for workflow {self.workflow_id}: {e}",
                    exc_info=True,
                )
                await asyncio.sleep(self.check_interval)

        logger.info(f"Email monitoring stopped for workflow {self.workflow_id}")

    async def _check_new_emails(self) -> None:
        """Check for new emails and process them"""
        imap_client = None

        try:
            # Connect to IMAP server
            imap_client = aioimaplib.IMAP4_SSL(host=self.imap_server, port=993)
            await imap_client.wait_hello_from_server()

            # Login
            login_result = await imap_client.login(self.email_user, self.email_password)
            if login_result.result != "OK":
                logger.error(f"IMAP login failed: {login_result}")
                return

            # Select folder
            select_result = await imap_client.select(self.folder)
            if select_result.result != "OK":
                logger.error(f"Failed to select folder {self.folder}: {select_result}")
                return

            # Search for unseen emails
            search_result = await imap_client.search("UNSEEN")
            if search_result.result != "OK":
                logger.debug(f"No new emails found for workflow {self.workflow_id}")
                return

            email_ids = search_result.lines[0].decode().split() if search_result.lines else []

            if not email_ids:
                logger.debug(f"No new emails found for workflow {self.workflow_id}")
                return

            logger.info(f"Found {len(email_ids)} new emails for workflow {self.workflow_id}")

            # Process each email
            for email_id in email_ids:
                try:
                    await self._process_email(imap_client, email_id)
                except Exception as e:
                    logger.error(f"Error processing email {email_id}: {e}", exc_info=True)

        except Exception as e:
            logger.error(
                f"Error checking emails for workflow {self.workflow_id}: {e}",
                exc_info=True,
            )

        finally:
            if imap_client:
                try:
                    await imap_client.logout()
                except Exception:
                    pass

    async def _process_email(self, imap_client: aioimaplib.IMAP4_SSL, email_id: str) -> None:
        """Process a single email"""
        try:
            # Fetch email
            fetch_result = await imap_client.fetch(email_id, "(RFC822)")
            if fetch_result.result != "OK":
                logger.error(f"Failed to fetch email {email_id}: {fetch_result}")
                return

            email_data = fetch_result.lines[1]
            email_message = email.message_from_bytes(email_data)

            # Extract email information
            email_info = await self._extract_email_info(email_message)

            # Apply email filter
            if not self._matches_filter(email_info):
                logger.debug(f"Email {email_id} does not match filter, skipping")
                return

            # Prepare trigger data
            trigger_data = {
                "trigger_type": self.trigger_type,
                "email_id": email_id,
                "subject": email_info["subject"],
                "sender": email_info["sender"],
                "recipient": email_info["recipient"],
                "date": email_info["date"],
                "body_text": email_info["body_text"],
                "body_html": email_info["body_html"],
                "attachments": email_info["attachments"]
                if self.attachment_processing == "include"
                else [],
                "triggered_at": datetime.utcnow().isoformat(),
            }

            # Trigger workflow
            result = await self._trigger_workflow(trigger_data)

            if result.status == ExecutionStatus.RUNNING:
                logger.info(
                    f"Email trigger executed successfully for workflow {self.workflow_id}: {result.execution_id}"
                )

                # Mark as read if configured
                if self.mark_as_read:
                    await imap_client.store(email_id, "+FLAGS", "\\Seen")

            else:
                logger.warning(
                    f"Email trigger execution had issues for workflow {self.workflow_id}: {result.message}"
                )

        except Exception as e:
            logger.error(
                f"Error processing email {email_id} for workflow {self.workflow_id}: {e}",
                exc_info=True,
            )

    async def _extract_email_info(
        self, email_message: email.message.EmailMessage
    ) -> Dict[str, Any]:
        """Extract information from email message"""
        try:
            email_info = {
                "subject": email_message.get("Subject", ""),
                "sender": email_message.get("From", ""),
                "recipient": email_message.get("To", ""),
                "date": email_message.get("Date", ""),
                "message_id": email_message.get("Message-ID", ""),
                "body_text": "",
                "body_html": "",
                "attachments": [],
            }

            # Extract body content
            if email_message.is_multipart():
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition", ""))

                    if "attachment" not in content_disposition:
                        if content_type == "text/plain":
                            email_info["body_text"] += part.get_payload(decode=True).decode(
                                "utf-8", errors="ignore"
                            )
                        elif content_type == "text/html":
                            email_info["body_html"] += part.get_payload(decode=True).decode(
                                "utf-8", errors="ignore"
                            )
                    else:
                        # Handle attachment
                        if self.attachment_processing == "include":
                            attachment_info = {
                                "filename": part.get_filename() or "unnamed",
                                "content_type": content_type,
                                "size": len(part.get_payload(decode=True))
                                if part.get_payload(decode=True)
                                else 0,
                            }

                            # For small attachments, include content (base64 encoded)
                            if attachment_info["size"] < 1024 * 1024:  # 1MB limit
                                attachment_content = part.get_payload(decode=True)
                                attachment_info["content"] = base64.b64encode(
                                    attachment_content
                                ).decode("utf-8")

                            email_info["attachments"].append(attachment_info)
            else:
                # Single part message
                content_type = email_message.get_content_type()
                content = email_message.get_payload(decode=True).decode("utf-8", errors="ignore")

                if content_type == "text/plain":
                    email_info["body_text"] = content
                elif content_type == "text/html":
                    email_info["body_html"] = content

            return email_info

        except Exception as e:
            logger.error(f"Error extracting email info: {e}", exc_info=True)
            return {
                "subject": "",
                "sender": "",
                "recipient": "",
                "date": "",
                "body_text": "",
                "body_html": "",
                "attachments": [],
            }

    def _matches_filter(self, email_info: Dict[str, Any]) -> bool:
        """Check if email matches the configured filter"""
        if not self.email_filter:
            return True

        try:
            # Simple filter format: "from:example@domain.com" or "subject:keyword"
            filter_parts = self.email_filter.strip().split(":")

            if len(filter_parts) != 2:
                # If no specific filter format, search in all text fields
                search_text = self.email_filter.lower()
                email_text = f"{email_info['subject']} {email_info['sender']} {email_info['body_text']}".lower()
                return search_text in email_text

            filter_type, filter_value = filter_parts
            filter_type = filter_type.lower().strip()
            filter_value = filter_value.lower().strip()

            if filter_type == "from":
                return filter_value in email_info["sender"].lower()
            elif filter_type == "subject":
                return filter_value in email_info["subject"].lower()
            elif filter_type == "to":
                return filter_value in email_info["recipient"].lower()
            elif filter_type == "body":
                body_text = f"{email_info['body_text']} {email_info['body_html']}".lower()
                return filter_value in body_text
            else:
                # Unknown filter type, default to subject search
                return filter_value in email_info["subject"].lower()

        except Exception as e:
            logger.error(f"Error applying email filter: {e}", exc_info=True)
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Return health status of the email trigger"""
        base_health = await super().health_check()

        email_health = {
            **base_health,
            "email_filter": self.email_filter,
            "folder": self.folder,
            "mark_as_read": self.mark_as_read,
            "check_interval": self.check_interval,
            "monitoring_active": self._monitoring_task is not None
            and not self._monitoring_task.done(),
            "imap_server": self.imap_server,
            "email_user": self.email_user[:5] + "***"
            if self.email_user
            else None,  # Partial email for privacy
        }

        return email_health
