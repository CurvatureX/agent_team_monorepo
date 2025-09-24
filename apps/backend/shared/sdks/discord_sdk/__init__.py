"""
Discord SDK for workflow automation.

This SDK provides a minimal Discord API client for bot-based operations,
aligned with common MCP server tool behaviors.
"""

from .client import DiscordAPIError, DiscordSDK

__all__ = [
    "DiscordSDK",
    "DiscordAPIError",
]
