#!/usr/bin/env python3
"""
Test script for Migadu email client with provided credentials
"""

import os
import sys

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from shared.sdks.email_client import EmailMessage, MigaduEmailClient


def test_migadu_connection():
    """Test Migadu SMTP connection and send test email"""

    # Test recipient
    test_recipient = "z1771485029@gmail.com"

    print("Testing Migadu email client...")
    print("Server: smtp.migadu.com")
    print("Port: 465 (SSL)")
    print(f"Test recipient: {test_recipient}")
    print("-" * 50)

    try:
        # Create Migadu client from environment variables
        client = MigaduEmailClient.from_env()

        print("✓ MigaduEmailClient created successfully from environment variables")

        # Test connection
        print("Testing SMTP connection...")
        if client.test_connection():
            print("✓ SMTP connection successful!")

            # Send test email
            test_message = EmailMessage(
                subject="🚀 Test Email from Starmates AI - Migadu SMTP Integration",
                body="""Hello!

This is a test email sent from the Starmates AI backend using Migadu SMTP service.

Email Integration Details:
- Sender: no_reply@starmates.ai (via Migadu)
- SMTP Server: smtp.migadu.com
- Port: 465 (SSL)
- Client: Custom Python Email SDK

If you received this email, it means our email integration is working perfectly!

Best regards,
Starmates AI Development Team

---
This is an automated test message. Please ignore if received unexpectedly.""",
                receiver_email=test_recipient,
                html_body="""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px;">
        <h1 style="margin: 0;">🚀 Starmates AI</h1>
        <p style="margin: 10px 0 0 0; font-size: 18px;">Email Integration Test</p>
    </div>

    <div style="background: #f9f9f9; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
        <h2 style="color: #4CAF50; margin-top: 0;">✅ Integration Successful!</h2>
        <p>This test email was sent from the <strong>Starmates AI backend</strong> using our custom email SDK with Migadu SMTP service.</p>
    </div>

    <div style="background: #fff; border: 1px solid #ddd; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
        <h3 style="margin-top: 0; color: #333;">📧 Email Integration Details:</h3>
        <ul style="margin: 0;">
            <li><strong>Sender:</strong> no_reply@starmates.ai (via Migadu)</li>
            <li><strong>SMTP Server:</strong> smtp.migadu.com</li>
            <li><strong>Port:</strong> 465 (SSL)</li>
            <li><strong>Client:</strong> Custom Python Email SDK</li>
        </ul>
    </div>

    <p>If you received this email, it means our email integration is working perfectly! 🎉</p>

    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 14px;">
        <p><strong>Best regards,</strong><br>
        Starmates AI Development Team</p>

        <p style="font-style: italic;">This is an automated test message. Please ignore if received unexpectedly.</p>
    </div>
</body>
</html>""",
            )

            print(f"Sending test email to {test_recipient}...")
            print("📧 Email details:")
            print(f"   From: {client.config.sender_email or client.config.smtp_username}")
            print(f"   To: {test_recipient}")
            print(f"   Subject: {test_message.subject}")

            if client.send_email(test_message):
                print("✅ Test email sent successfully!")
                print(f"📧 Check {test_recipient} for the test email")
                print("💡 Tips if email not received:")
                print("   - Check spam/junk folder")
                print("   - Wait a few minutes for delivery")
                print("   - Verify recipient email address")
                print("   - Check Migadu sending limits")
                return True
            else:
                print("❌ Failed to send test email")
                return False

        else:
            print("✗ SMTP connection failed")
            return False

    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


def test_starttls_mode():
    """Test STARTTLS mode (port 587) as alternative"""

    username = "no_reply@starmates.ai"
    password = "#g6pa4xJN*JMX8!"

    print("\nTesting STARTTLS mode (port 587)...")
    print("-" * 50)

    try:
        # Create client with STARTTLS mode
        client = MigaduEmailClient(
            username=username,
            password=password,
            sender_name="Starmates AI",
            use_starttls=True,  # This uses port 587
        )

        print("✓ MigaduEmailClient (STARTTLS) created successfully")

        # Test connection
        print("Testing STARTTLS connection...")
        if client.test_connection():
            print("✓ STARTTLS connection successful!")
            return True
        else:
            print("✗ STARTTLS connection failed")
            return False

    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


if __name__ == "__main__":
    print("Migadu Email Client Test")
    print("=" * 50)

    # Test SSL mode (port 465) and send actual test email
    ssl_success = test_migadu_connection()

    print("\n" + "=" * 50)
    print("TEST RESULTS:")
    print(f"SSL Mode (Port 465) + Email Send: {'✅ PASS' if ssl_success else '❌ FAIL'}")

    if ssl_success:
        print("\n🎉 Migadu email integration is working perfectly!")
        print("📧 Test email has been sent to z1771485029@gmail.com")
        print("💡 The email client is ready for production use!")
    else:
        print("\n❌ Email test failed. Please check:")
        print("  - Environment variables in .env file")
        print("  - Network connectivity")
        print("  - Migadu credentials")
