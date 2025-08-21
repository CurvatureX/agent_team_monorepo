"""
Notion API data models for structured data handling.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class NotionObjectType(Enum):
    """Notion object types."""

    PAGE = "page"
    DATABASE = "database"
    BLOCK = "block"
    USER = "user"
    WORKSPACE = "workspace"


class PropertyType(Enum):
    """Notion property types."""

    TITLE = "title"
    RICH_TEXT = "rich_text"
    NUMBER = "number"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    DATE = "date"
    FORMULA = "formula"
    RELATION = "relation"
    ROLLUP = "rollup"
    PEOPLE = "people"
    FILES = "files"
    CHECKBOX = "checkbox"
    URL = "url"
    EMAIL = "email"
    PHONE_NUMBER = "phone_number"
    CREATED_TIME = "created_time"
    CREATED_BY = "created_by"
    LAST_EDITED_TIME = "last_edited_time"
    LAST_EDITED_BY = "last_edited_by"
    VERIFICATION = "verification"
    UNIQUE_ID = "unique_id"
    STATUS = "status"


class BlockType(Enum):
    """Notion block types."""

    PARAGRAPH = "paragraph"
    HEADING_1 = "heading_1"
    HEADING_2 = "heading_2"
    HEADING_3 = "heading_3"
    BULLETED_LIST_ITEM = "bulleted_list_item"
    NUMBERED_LIST_ITEM = "numbered_list_item"
    TO_DO = "to_do"
    TOGGLE = "toggle"
    CHILD_PAGE = "child_page"
    CHILD_DATABASE = "child_database"
    EMBED = "embed"
    IMAGE = "image"
    VIDEO = "video"
    FILE = "file"
    PDF = "pdf"
    BOOKMARK = "bookmark"
    CALLOUT = "callout"
    QUOTE = "quote"
    EQUATION = "equation"
    DIVIDER = "divider"
    TABLE_OF_CONTENTS = "table_of_contents"
    BREADCRUMB = "breadcrumb"
    COLUMN_LIST = "column_list"
    COLUMN = "column"
    LINK_PREVIEW = "link_preview"
    SYNCED_BLOCK = "synced_block"
    TEMPLATE = "template"
    LINK_TO_PAGE = "link_to_page"
    TABLE = "table"
    TABLE_ROW = "table_row"
    CODE = "code"


@dataclass
class NotionUser:
    """Notion user model."""

    id: str
    type: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    person_email: Optional[str] = None
    bot_name: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NotionUser":
        """Create NotionUser from API response."""
        return cls(
            id=data["id"],
            type=data.get("type", "user"),  # Default to "user" if type missing
            name=data.get("name"),
            avatar_url=data.get("avatar_url"),
            person_email=data.get("person", {}).get("email") if data.get("person") else None,
            bot_name=data.get("bot", {}).get("name") if data.get("bot") else None,
        )


@dataclass
class NotionProperty:
    """Notion property model."""

    id: str
    name: str
    type: PropertyType
    value: Any

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> "NotionProperty":
        """Create NotionProperty from API response."""
        prop_type = PropertyType(data["type"])

        # Extract value based on property type
        value = None
        if prop_type == PropertyType.TITLE:
            value = data.get("title", [{}])[0].get("plain_text", "") if data.get("title") else ""
        elif prop_type == PropertyType.RICH_TEXT:
            value = (
                data.get("rich_text", [{}])[0].get("plain_text", "")
                if data.get("rich_text")
                else ""
            )
        elif prop_type == PropertyType.NUMBER:
            value = data.get("number")
        elif prop_type == PropertyType.SELECT:
            select_data = data.get("select")
            value = select_data.get("name") if select_data else None
        elif prop_type == PropertyType.MULTI_SELECT:
            value = [item.get("name") for item in data.get("multi_select", [])]
        elif prop_type == PropertyType.DATE:
            date_data = data.get("date")
            value = date_data.get("start") if date_data else None
        elif prop_type == PropertyType.CHECKBOX:
            value = data.get("checkbox", False)
        elif prop_type == PropertyType.URL:
            value = data.get("url")
        elif prop_type == PropertyType.EMAIL:
            value = data.get("email")
        elif prop_type == PropertyType.PHONE_NUMBER:
            value = data.get("phone_number")
        elif prop_type == PropertyType.PEOPLE:
            value = [NotionUser.from_dict(user) for user in data.get("people", [])]
        elif prop_type in [PropertyType.CREATED_TIME, PropertyType.LAST_EDITED_TIME]:
            value = data.get(prop_type.value)
        elif prop_type in [PropertyType.CREATED_BY, PropertyType.LAST_EDITED_BY]:
            user_data = data.get(prop_type.value)
            value = NotionUser.from_dict(user_data) if user_data else None
        else:
            value = data.get(prop_type.value)

        return cls(id=data.get("id", ""), name=name, type=prop_type, value=value)


@dataclass
class NotionBlock:
    """Notion block model."""

    id: str
    type: BlockType
    has_children: bool
    archived: bool
    created_time: datetime
    created_by: NotionUser
    last_edited_time: datetime
    last_edited_by: NotionUser
    content: Dict[str, Any]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NotionBlock":
        """Create NotionBlock from API response."""
        return cls(
            id=data["id"],
            type=BlockType(data["type"]),
            has_children=data.get("has_children", False),
            archived=data.get("archived", False),
            created_time=datetime.fromisoformat(data["created_time"].replace("Z", "+00:00")),
            created_by=NotionUser.from_dict(data["created_by"]),
            last_edited_time=datetime.fromisoformat(
                data["last_edited_time"].replace("Z", "+00:00")
            ),
            last_edited_by=NotionUser.from_dict(data["last_edited_by"]),
            content=data.get(data["type"], {}),
        )


@dataclass
class NotionPage:
    """Notion page model."""

    id: str
    created_time: datetime
    created_by: NotionUser
    last_edited_time: datetime
    last_edited_by: NotionUser
    archived: bool
    icon: Optional[Dict[str, Any]]
    cover: Optional[Dict[str, Any]]
    properties: Dict[str, NotionProperty]
    parent: Dict[str, Any]
    url: str
    public_url: Optional[str]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NotionPage":
        """Create NotionPage from API response."""
        properties = {}
        for prop_name, prop_data in data.get("properties", {}).items():
            properties[prop_name] = NotionProperty.from_dict(prop_name, prop_data)

        return cls(
            id=data["id"],
            created_time=datetime.fromisoformat(data["created_time"].replace("Z", "+00:00")),
            created_by=NotionUser.from_dict(data["created_by"]),
            last_edited_time=datetime.fromisoformat(
                data["last_edited_time"].replace("Z", "+00:00")
            ),
            last_edited_by=NotionUser.from_dict(data["last_edited_by"]),
            archived=data.get("archived", False),
            icon=data.get("icon"),
            cover=data.get("cover"),
            properties=properties,
            parent=data.get("parent", {}),
            url=data["url"],
            public_url=data.get("public_url"),
        )


@dataclass
class NotionDatabase:
    """Notion database model."""

    id: str
    created_time: datetime
    created_by: NotionUser
    last_edited_time: datetime
    last_edited_by: NotionUser
    title: List[Dict[str, Any]]
    description: List[Dict[str, Any]]
    icon: Optional[Dict[str, Any]]
    cover: Optional[Dict[str, Any]]
    properties: Dict[str, Dict[str, Any]]
    parent: Dict[str, Any]
    url: str
    public_url: Optional[str]
    archived: bool
    is_inline: bool

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NotionDatabase":
        """Create NotionDatabase from API response."""
        return cls(
            id=data["id"],
            created_time=datetime.fromisoformat(data["created_time"].replace("Z", "+00:00")),
            created_by=NotionUser.from_dict(data["created_by"]),
            last_edited_time=datetime.fromisoformat(
                data["last_edited_time"].replace("Z", "+00:00")
            ),
            last_edited_by=NotionUser.from_dict(data["last_edited_by"]),
            title=data.get("title", []),
            description=data.get("description", []),
            icon=data.get("icon"),
            cover=data.get("cover"),
            properties=data.get("properties", {}),
            parent=data.get("parent", {}),
            url=data["url"],
            public_url=data.get("public_url"),
            archived=data.get("archived", False),
            is_inline=data.get("is_inline", False),
        )


@dataclass
class NotionSearchResult:
    """Notion search result model."""

    object_type: NotionObjectType
    id: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NotionSearchResult":
        """Create NotionSearchResult from API response."""
        return cls(object_type=NotionObjectType(data["object"]), id=data["id"])
