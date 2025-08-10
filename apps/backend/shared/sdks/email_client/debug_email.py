#!/usr/bin/env python3
"""
Debug email sending with detailed SMTP logging - Workflow Scheduler Configuration
"""

import logging
import os
import smtplib
import sys

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from shared.sdks.email_client import EmailConfig, EmailMessage, SMTPEmailClient

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def debug_email_send():
    """Send email with full debug logging using generic SMTP configuration"""

    test_recipient = "test-fqnzwtaif@srv1.mail-tester.com"

    print("Debug Email Send Test - Workflow Scheduler Configuration")
    print("=" * 50)

    # Check environment variables - now using SMTP_* format
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    sender_name = os.getenv("SMTP_SENDER_NAME")
    sender_email = os.getenv("SMTP_SENDER_EMAIL")

    print(f"Environment variables:")
    print(f"   SMTP_USERNAME: {username}")
    print(f"   SMTP_PASSWORD: {'*' * len(password) if password else 'NOT SET'}")
    print(f"   SMTP_SENDER_NAME: {sender_name}")
    print(f"   SMTP_SENDER_EMAIL: {sender_email}")
    print("-" * 50)

    try:
        # Manual SMTP test first
        print("Testing raw SMTP connection...")
        smtp = smtplib.SMTP_SSL("smtp.migadu.com", 465, timeout=30)
        smtp.set_debuglevel(1)  # Enable SMTP debug
        smtp.login(username, password)
        print("✅ Raw SMTP login successful")

        # Create simple test message
        from email.mime.text import MIMEText

        msg = MIMEText("This is a test message from Workflow Scheduler - Starmates AI")
        msg["Subject"] = "🔧 Workflow Scheduler Email Test"
        msg["From"] = f"{sender_name} <{sender_email}>" if sender_name else sender_email
        msg["To"] = test_recipient

        print(f"Sending simple message to {test_recipient}...")
        print(f"   From: {msg['From']}")
        print(f"   Subject: {msg['Subject']}")
        smtp.send_message(msg)
        smtp.quit()
        print("✅ Simple message sent via raw SMTP")

        # Now test with our generic SMTP client
        print("\nTesting with SMTPEmailClient (from_env)...")

        # Create client using generic SMTP configuration
        config = EmailConfig.from_env()
        client = SMTPEmailClient(config)

        print(f"Configuration loaded:")
        print(f"   Host: {config.smtp_host}")
        print(f"   Port: {config.smtp_port}")
        print(f"   Username: {config.smtp_username}")
        print(f"   Sender Name: {config.sender_name}")
        print(f"   Sender Email: {config.sender_email}")
        print(f"   Use SSL: {config.use_ssl}")
        print(f"   Use TLS: {config.use_tls}")

        workflow_message = EmailMessage(
            subject="🚀 Workflow Scheduler Test Email",
            body="""Hello!

This is a test email from the Workflow Scheduler service using the Starmates AI email client SDK.

Service Details:
- Service: Workflow Scheduler
- Sender: Workflow Scheduler <no_reply@starmates.ai>
- SMTP Provider: Migadu
- Configuration: SMTP_* environment variables

This email confirms that the Workflow Scheduler can successfully send email notifications.

Best regards,
Workflow Scheduler Service
Starmates AI Platform

---
This is an automated test message from the Workflow Scheduler service.""",
            receiver_email=test_recipient,
            html_body="""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #FF6B6B 0%, #4ECDC4 100%); color: white; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px;">
        <h1 style="margin: 0;">🚀 Workflow Scheduler</h1>
        <p style="margin: 10px 0 0 0; font-size: 18px;">Email Integration Test</p>
    </div>

    <div style="background: #f9f9f9; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
        <h2 style="color: #4CAF50; margin-top: 0;">✅ Email Service Active!</h2>
        <p>This test email was sent from the <strong>Workflow Scheduler</strong> service using the Starmates AI email client SDK.</p>
    </div>

    <div style="background: #fff; border: 1px solid #ddd; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
        <h3 style="margin-top: 0; color: #333;">🔧 Service Details:</h3>
        <ul style="margin: 0;">
            <li><strong>Service:</strong> Workflow Scheduler</li>
            <li><strong>Sender:</strong> Workflow Scheduler &lt;no_reply@starmates.ai&gt;</li>
            <li><strong>SMTP Provider:</strong> Migadu</li>
            <li><strong>Configuration:</strong> SMTP_* environment variables</li>
        </ul>
    </div>

    <p>This email confirms that the <strong>Workflow Scheduler</strong> can successfully send email notifications. 🎉</p>

    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 14px;">
        <p><strong>Best regards,</strong><br>
        Workflow Scheduler Service<br>
        <strong>Starmates AI Platform</strong></p>

        <p style="font-style: italic;">This is an automated test message from the Workflow Scheduler service.</p>
    </div>
</body>
</html>""",
        )

        success = client.send_email(workflow_message)
        print(f"Workflow Scheduler email send result: {success}")

        return success

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    debug_email_send()
