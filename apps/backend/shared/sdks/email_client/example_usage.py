#!/usr/bin/env python3
"""
Example usage of Migadu email client for Starmates AI services
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from shared.sdks.email_client import BulkEmailMessage, EmailMessage, MigaduEmailClient

# Starmates AI email configuration
STARMATES_EMAIL_CONFIG = {
    "username": "no_reply@starmates.ai",
    "password": "#g6pa4xJN*JMX8!",
    "sender_name": "Starmates AI",
}


def create_starmates_email_client():
    """Create email client for Starmates AI services"""
    return MigaduEmailClient(**STARMATES_EMAIL_CONFIG)


def send_welcome_email(user_email: str, user_name: str):
    """Send welcome email to new user"""
    client = create_starmates_email_client()

    message = EmailMessage(
        subject="Welcome to Starmates AI! 🚀",
        body=f"""Hi {user_name},

Welcome to Starmates AI! We're excited to have you on board.

Your AI team is ready to help you automate workflows and boost productivity.

Get started:
1. Create your first workflow
2. Set up automation rules
3. Invite team members

If you need help, just reply to this email.

Best regards,
The Starmates AI Team""",
        receiver_email=user_email,
        html_body=f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h1 style="color: #4CAF50;">Welcome to Starmates AI! 🚀</h1>

        <p>Hi <strong>{user_name}</strong>,</p>

        <p>Welcome to Starmates AI! We're excited to have you on board.</p>

        <p>Your AI team is ready to help you automate workflows and boost productivity.</p>

        <div style="background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <h3>Get started:</h3>
            <ol>
                <li>Create your first workflow</li>
                <li>Set up automation rules</li>
                <li>Invite team members</li>
            </ol>
        </div>

        <p>If you need help, just reply to this email.</p>

        <p>Best regards,<br>
        <strong>The Starmates AI Team</strong></p>
    </div>
</body>
</html>""",
    )

    success = client.send_email(message)
    if success:
        print(f"✓ Welcome email sent to {user_email}")
    else:
        print(f"✗ Failed to send welcome email to {user_email}")

    return success


def send_notification_email(user_email: str, subject: str, message: str):
    """Send notification email"""
    client = create_starmates_email_client()

    email = EmailMessage(
        subject=f"[Starmates AI] {subject}",
        body=f"""Hello,

{message}

---
This is an automated notification from Starmates AI.
If you have questions, please contact support.

Best regards,
Starmates AI Team""",
        receiver_email=user_email,
    )

    return client.send_email(email)


def send_bulk_announcement(user_emails: list, subject: str, content: str):
    """Send bulk announcement to multiple users"""
    client = create_starmates_email_client()

    bulk_message = BulkEmailMessage(
        subject=f"[Starmates AI] {subject}",
        body=f"""Hello,

{content}

Best regards,
The Starmates AI Team

---
You're receiving this because you're a valued member of Starmates AI.
""",
        receiver_emails=user_emails,
    )

    results = client.send_bulk_email(bulk_message)

    success_count = sum(1 for success in results.values() if success)
    total_count = len(results)

    print(f"Bulk email results: {success_count}/{total_count} successful")
    for email, success in results.items():
        status = "✓" if success else "✗"
        print(f"  {status} {email}")

    return results


# Example usage in your services
if __name__ == "__main__":
    print("Starmates AI Email Client Examples")
    print("=" * 50)

    # Example 1: Welcome email
    print("\n1. Testing welcome email...")
    # send_welcome_email("test@example.com", "John Doe")

    # Example 2: Notification email
    print("\n2. Testing notification email...")
    # send_notification_email("test@example.com", "Workflow Completed", "Your automation workflow has finished successfully.")

    # Example 3: Bulk announcement
    print("\n3. Testing bulk announcement...")
    # send_bulk_announcement(
    #     ["user1@example.com", "user2@example.com"],
    #     "New Feature Available",
    #     "We've just released exciting new automation features!"
    # )

    print("\nUncomment the function calls above to test sending emails.")
    print("Remember to replace example emails with real test addresses.")
