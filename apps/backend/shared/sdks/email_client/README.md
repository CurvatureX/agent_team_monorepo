# Email Client SDK

A shared email client SDK for sending emails across backend services, optimized for Migadu SMTP service.

## Features

- Send single emails
- Send bulk emails (group sending)
- Support for HTML and plain text content
- File attachments support
- Configurable SMTP settings
- Comprehensive error handling and logging
- Test connection functionality
- **Migadu-specific optimization** with pre-configured SSL/STARTTLS settings

## Quick Start with Migadu

### Recommended: Using MigaduEmailClient

```python
from shared.email_client import MigaduEmailClient, EmailMessage

# Method 1: Direct initialization (SSL - port 465, recommended)
email_client = MigaduEmailClient(
    username="your-email@yourdomain.com",
    password="your-password",
    sender_name="Your Service Name"
)

# Method 2: Using STARTTLS (port 587)
email_client = MigaduEmailClient(
    username="your-email@yourdomain.com",
    password="your-password",
    sender_name="Your Service Name",
    use_starttls=True
)

# Method 3: From environment variables
email_client = MigaduEmailClient.from_env()
```

### Generic Setup (Other SMTP Providers)

```python
from shared.email_client import SMTPEmailClient, EmailConfig, EmailMessage

# Create configuration from environment variables (defaults to Migadu)
config = EmailConfig.from_env()

# Or create configuration manually
config = EmailConfig(
    smtp_host="smtp.your-provider.com",
    smtp_port=587,
    smtp_username="your-email@domain.com",
    smtp_password="your-password",
    use_tls=True,
    sender_email="your-email@domain.com",
    sender_name="Your Service Name"
)

# Initialize client
email_client = SMTPEmailClient(config)
```

### Send Single Email

```python
message = EmailMessage(
    subject="Test Email",
    body="This is a test email.",
    receiver_email="recipient@example.com",
    html_body="<h1>This is a test email</h1>",  # Optional
    attachments=["/path/to/file.pdf"]  # Optional
)

success = email_client.send_email(message)
if success:
    print("Email sent successfully!")
else:
    print("Failed to send email")
```

### Send Bulk Emails

```python
from shared.email_client import BulkEmailMessage

bulk_message = BulkEmailMessage(
    subject="Newsletter",
    body="This is our monthly newsletter.",
    receiver_emails=[
        "user1@example.com",
        "user2@example.com",
        "user3@example.com"
    ],
    html_body="<h1>Monthly Newsletter</h1><p>This is our monthly newsletter.</p>"
)

results = email_client.send_bulk_email(bulk_message)
for email, success in results.items():
    print(f"{email}: {'✓' if success else '✗'}")
```

### Test Connection

```python
if email_client.test_connection():
    print("SMTP connection successful!")
else:
    print("SMTP connection failed")
```

## Environment Variables

### For Migadu (Recommended)

Set these environment variables for Migadu configuration:

```bash
# Migadu-specific (preferred)
MIGADU_USERNAME=your-email@yourdomain.com
MIGADU_PASSWORD=your-password
MIGADU_SENDER_EMAIL=your-email@yourdomain.com  # Optional, defaults to username
MIGADU_SENDER_NAME="Your Service Name"         # Optional
MIGADU_USE_STARTTLS=false                      # Optional, default: false (uses SSL port 465)

# Or use generic SMTP variables (automatically configured for Migadu)
SMTP_HOST=smtp.migadu.com                      # Default for from_env()
SMTP_PORT=465                                  # Default for from_env()
SMTP_USERNAME=your-email@yourdomain.com
SMTP_PASSWORD=your-password
SMTP_USE_TLS=false                             # Default for Migadu SSL
SMTP_USE_SSL=true                              # Default for Migadu SSL
SMTP_SENDER_EMAIL=your-email@yourdomain.com
SMTP_SENDER_NAME="Your Service Name"
SMTP_TIMEOUT=30
```

### For Other SMTP Providers

```bash
# Generic SMTP configuration
SMTP_HOST=smtp.your-provider.com
SMTP_PORT=587
SMTP_USERNAME=your-email@domain.com
SMTP_PASSWORD=your-password
SMTP_USE_TLS=true
SMTP_USE_SSL=false
SMTP_SENDER_EMAIL=your-email@domain.com
SMTP_SENDER_NAME="Your Service Name"
SMTP_TIMEOUT=30
```

## Migadu Setup

For Migadu email service:

1. **Sign up** for a Migadu account at [migadu.com](https://migadu.com)
2. **Add your domain** and verify DNS settings
3. **Create a mailbox** for your application
4. **Use your full email address** as username (e.g., `noreply@yourdomain.com`)
5. **Use your mailbox password** as password

### Migadu Configuration Options

**SSL (Port 465) - Recommended:**
- More reliable and secure
- Default configuration for `MigaduEmailClient`
- Use `use_starttls=False` (default)

**STARTTLS (Port 587) - Alternative:**
- Standard TLS encryption
- Use `use_starttls=True`

## Gmail Setup (Alternative)

For Gmail, you'll need to:

1. Enable 2-factor authentication
2. Generate an App Password
3. Use the App Password as `SMTP_PASSWORD`
4. Use `smtp.gmail.com` as host

## Error Handling

The SDK includes comprehensive error handling:

- Connection failures are logged and return `False`
- Individual email failures in bulk sending are tracked per recipient
- File attachment errors are logged but don't stop email sending
- Configuration validation prevents runtime errors

## Logging

The SDK uses Python's standard logging module. Configure logging in your service:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

Log messages include:
- Successful email sends
- Connection errors
- Individual failure details
- Missing attachment warnings
