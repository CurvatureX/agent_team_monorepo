import os
import random


def generate_random_icon_url() -> str:
    """
    Generate a random icon URL using DNS_DOMAIN_NAME and a random ID from 1 to 11.

    Returns:
        str: The generated icon URL in format {DNS_DOMAIN_NAME}/{id}.png
    """
    dns_domain_name = os.getenv("DNS_DOMAIN_NAME", "")
    if not dns_domain_name:
        raise ValueError("DNS_DOMAIN_NAME environment variable is not set")

    # Generate random ID from 1 to 11
    icon_id = random.randint(1, 11)

    return f"{dns_domain_name}/{icon_id}.png"
