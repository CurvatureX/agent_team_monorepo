#!/usr/bin/env python3
"""
Debug email sending with detailed SMTP logging
"""

import logging
import os
import smtplib
import sys

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from shared.email_client import EmailMessage, MigaduEmailClient

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def debug_email_send():
    """Send email with full debug logging"""

    test_recipient = "z1771485029@gmail.com"

    print("Debug Email Send Test")
    print("=" * 50)

    # Check environment variables
    username = os.getenv("MIGADU_USERNAME")
    password = os.getenv("MIGADU_PASSWORD")
    sender_name = os.getenv("MIGADU_SENDER_NAME")

    print(f"Environment variables:")
    print(f"   MIGADU_USERNAME: {username}")
    print(f"   MIGADU_PASSWORD: {'*' * len(password) if password else 'NOT SET'}")
    print(f"   MIGADU_SENDER_NAME: {sender_name}")
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

        msg = MIMEText("This is a simple test message from Starmates AI")
        msg["Subject"] = "Simple Test from Starmates AI"
        msg["From"] = username
        msg["To"] = test_recipient

        print(f"Sending simple message to {test_recipient}...")
        smtp.send_message(msg)
        smtp.quit()
        print("✅ Simple message sent via raw SMTP")

        # Now test with our client
        print("\nTesting with MigaduEmailClient...")
        client = MigaduEmailClient.from_env()

        simple_message = EmailMessage(
            subject="Test from Starmates AI Email Client",
            body="This is a test message from our custom email client.",
            receiver_email=test_recipient,
        )

        success = client.send_email(simple_message)
        print(f"Client send result: {success}")

        return True

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    debug_email_send()
