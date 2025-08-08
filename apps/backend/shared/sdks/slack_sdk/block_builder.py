"""
Slack Block Kit builder utilities.

Provides helper functions for building Slack Block Kit blocks and elements
for rich message formatting.
"""

from typing import Any, Dict, List, Optional, Union


class SlackBlockBuilder:
    """
    Utility class for building Slack Block Kit elements.

    Provides convenient methods to create various Slack block types
    for rich message formatting.
    """

    @staticmethod
    def section(
        text: str,
        text_type: str = "mrkdwn",
        accessory: Optional[Dict] = None,
        fields: Optional[List[Dict]] = None,
        block_id: Optional[str] = None,
    ) -> Dict:
        """
        Create a section block.

        Args:
            text: Section text content
            text_type: Text type ("mrkdwn" or "plain_text")
            accessory: Optional accessory element
            fields: Optional list of field objects
            block_id: Optional block ID

        Returns:
            Section block dictionary
        """
        block = {"type": "section", "text": {"type": text_type, "text": text}}

        if accessory:
            block["accessory"] = accessory
        if fields:
            block["fields"] = fields
        if block_id:
            block["block_id"] = block_id

        return block

    @staticmethod
    def divider(block_id: Optional[str] = None) -> Dict:
        """
        Create a divider block.

        Args:
            block_id: Optional block ID

        Returns:
            Divider block dictionary
        """
        block = {"type": "divider"}
        if block_id:
            block["block_id"] = block_id
        return block

    @staticmethod
    def header(text: str, block_id: Optional[str] = None) -> Dict:
        """
        Create a header block.

        Args:
            text: Header text
            block_id: Optional block ID

        Returns:
            Header block dictionary
        """
        block = {"type": "header", "text": {"type": "plain_text", "text": text}}

        if block_id:
            block["block_id"] = block_id

        return block

    @staticmethod
    def context(
        elements: List[Dict],
        block_id: Optional[str] = None,
    ) -> Dict:
        """
        Create a context block.

        Args:
            elements: List of context elements
            block_id: Optional block ID

        Returns:
            Context block dictionary
        """
        block = {"type": "context", "elements": elements}

        if block_id:
            block["block_id"] = block_id

        return block

    @staticmethod
    def text_element(text: str, text_type: str = "mrkdwn") -> Dict:
        """
        Create a text element.

        Args:
            text: Text content
            text_type: Text type ("mrkdwn" or "plain_text")

        Returns:
            Text element dictionary
        """
        return {"type": text_type, "text": text}

    @staticmethod
    def button(
        text: str,
        action_id: str,
        value: Optional[str] = None,
        url: Optional[str] = None,
        style: Optional[str] = None,
        confirm: Optional[Dict] = None,
    ) -> Dict:
        """
        Create a button element.

        Args:
            text: Button text
            action_id: Action ID for the button
            value: Optional value sent with action
            url: Optional URL to open
            style: Button style ("primary" or "danger")
            confirm: Optional confirmation dialog

        Returns:
            Button element dictionary
        """
        button = {
            "type": "button",
            "text": {"type": "plain_text", "text": text},
            "action_id": action_id,
        }

        if value:
            button["value"] = value
        if url:
            button["url"] = url
        if style:
            button["style"] = style
        if confirm:
            button["confirm"] = confirm

        return button

    @staticmethod
    def actions(
        elements: List[Dict],
        block_id: Optional[str] = None,
    ) -> Dict:
        """
        Create an actions block.

        Args:
            elements: List of interactive elements
            block_id: Optional block ID

        Returns:
            Actions block dictionary
        """
        block = {"type": "actions", "elements": elements}

        if block_id:
            block["block_id"] = block_id

        return block

    @staticmethod
    def fields(*field_texts: str) -> List[Dict]:
        """
        Create a list of field objects for sections.

        Args:
            *field_texts: Variable number of field text strings

        Returns:
            List of field dictionaries
        """
        return [{"type": "mrkdwn", "text": field_text} for field_text in field_texts]

    @classmethod
    def simple_message(cls, text: str, pretext: Optional[str] = None) -> List[Dict]:
        """
        Create a simple message with optional pretext.

        Args:
            text: Main message text
            pretext: Optional introductory text

        Returns:
            List of blocks for the message
        """
        blocks = []

        if pretext:
            blocks.append(cls.section(pretext))
            blocks.append(cls.divider())

        blocks.append(cls.section(text))

        return blocks

    @classmethod
    def notification_message(
        cls,
        title: str,
        message: str,
        status: str = "info",
        timestamp: Optional[str] = None,
        actions: Optional[List[Dict]] = None,
    ) -> List[Dict]:
        """
        Create a notification message with title, status, and optional actions.

        Args:
            title: Notification title
            message: Notification message
            status: Status type (info, success, warning, error)
            timestamp: Optional timestamp
            actions: Optional list of action elements

        Returns:
            List of blocks for the notification
        """
        status_emoji = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌"}

        emoji = status_emoji.get(status, "ℹ️")
        blocks = [cls.header(f"{emoji} {title}"), cls.section(message)]

        if timestamp:
            blocks.append(cls.context([cls.text_element(f"🕒 {timestamp}", "mrkdwn")]))

        if actions:
            blocks.append(cls.actions(actions))

        return blocks
