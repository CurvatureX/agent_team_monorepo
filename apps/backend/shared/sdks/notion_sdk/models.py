"""
Data models for Notion SDK.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Union


@dataclass
class RichText:
    """Represents Notion rich text."""
    type: str = "text"
    content: str = ""
    annotations: Optional[Dict[str, Any]] = None
    href: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RichText':
        """Create RichText from Notion API response."""
        text_data = data.get("text", {})
        return cls(
            type=data.get("type", "text"),
            content=text_data.get("content", ""),
            annotations=data.get("annotations"),
            href=text_data.get("link", {}).get("url") if text_data.get("link") else None
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to Notion API format."""
        result = {
            "type": self.type,
            "text": {"content": self.content}
        }
        if self.annotations:
            result["annotations"] = self.annotations
        if self.href:
            result["text"]["link"] = {"url": self.href}
        return result
    
    @classmethod
    def from_string(cls, text: str) -> 'RichText':
        """Create RichText from plain string."""
        return cls(content=text)


@dataclass
class User:
    """Represents a Notion user."""
    id: str
    type: str  # "person" or "bot"
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    email: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Create User from Notion API response."""
        person = data.get("person", {})
        bot = data.get("bot", {})
        
        return cls(
            id=data.get("id", ""),
            type=data.get("type", "person"),
            name=data.get("name"),
            avatar_url=data.get("avatar_url"),
            email=person.get("email") if person else None
        )


@dataclass
class Database:
    """Represents a Notion database."""
    id: str
    title: List[RichText]
    description: Optional[List[RichText]] = None
    properties: Optional[Dict[str, Any]] = None
    parent: Optional[Dict[str, Any]] = None
    url: Optional[str] = None
    archived: bool = False
    created_time: Optional[datetime] = None
    last_edited_time: Optional[datetime] = None
    icon: Optional[Dict[str, Any]] = None
    cover: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Database':
        """Create Database from Notion API response."""
        title = []
        if data.get("title"):
            title = [RichText.from_dict(rt) for rt in data["title"]]
        
        description = None
        if data.get("description"):
            description = [RichText.from_dict(rt) for rt in data["description"]]
        
        created_time = None
        if data.get("created_time"):
            try:
                created_time = datetime.fromisoformat(data["created_time"].replace('Z', '+00:00'))
            except ValueError:
                pass
        
        last_edited_time = None
        if data.get("last_edited_time"):
            try:
                last_edited_time = datetime.fromisoformat(data["last_edited_time"].replace('Z', '+00:00'))
            except ValueError:
                pass
        
        return cls(
            id=data.get("id", ""),
            title=title,
            description=description,
            properties=data.get("properties"),
            parent=data.get("parent"),
            url=data.get("url"),
            archived=data.get("archived", False),
            created_time=created_time,
            last_edited_time=last_edited_time,
            icon=data.get("icon"),
            cover=data.get("cover")
        )


@dataclass
class Page:
    """Represents a Notion page."""
    id: str
    properties: Dict[str, Any]
    parent: Dict[str, Any]
    url: Optional[str] = None
    archived: bool = False
    created_time: Optional[datetime] = None
    last_edited_time: Optional[datetime] = None
    created_by: Optional[User] = None
    last_edited_by: Optional[User] = None
    icon: Optional[Dict[str, Any]] = None
    cover: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Page':
        """Create Page from Notion API response."""
        created_time = None
        if data.get("created_time"):
            try:
                created_time = datetime.fromisoformat(data["created_time"].replace('Z', '+00:00'))
            except ValueError:
                pass
        
        last_edited_time = None
        if data.get("last_edited_time"):
            try:
                last_edited_time = datetime.fromisoformat(data["last_edited_time"].replace('Z', '+00:00'))
            except ValueError:
                pass
        
        created_by = None
        if data.get("created_by"):
            created_by = User.from_dict(data["created_by"])
        
        last_edited_by = None
        if data.get("last_edited_by"):
            last_edited_by = User.from_dict(data["last_edited_by"])
        
        return cls(
            id=data.get("id", ""),
            properties=data.get("properties", {}),
            parent=data.get("parent", {}),
            url=data.get("url"),
            archived=data.get("archived", False),
            created_time=created_time,
            last_edited_time=last_edited_time,
            created_by=created_by,
            last_edited_by=last_edited_by,
            icon=data.get("icon"),
            cover=data.get("cover")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to Notion API format for creation/update."""
        result = {
            "parent": self.parent,
            "properties": self.properties
        }
        
        if self.icon:
            result["icon"] = self.icon
        if self.cover:
            result["cover"] = self.cover
        if self.archived is not None:
            result["archived"] = self.archived
        
        return result


@dataclass
class Block:
    """Represents a Notion block."""
    id: Optional[str] = None
    type: str = "paragraph"
    has_children: bool = False
    archived: bool = False
    created_time: Optional[datetime] = None
    last_edited_time: Optional[datetime] = None
    content: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Block':
        """Create Block from Notion API response."""
        created_time = None
        if data.get("created_time"):
            try:
                created_time = datetime.fromisoformat(data["created_time"].replace('Z', '+00:00'))
            except ValueError:
                pass
        
        last_edited_time = None
        if data.get("last_edited_time"):
            try:
                last_edited_time = datetime.fromisoformat(data["last_edited_time"].replace('Z', '+00:00'))
            except ValueError:
                pass
        
        block_type = data.get("type", "paragraph")
        content = data.get(block_type)
        
        return cls(
            id=data.get("id"),
            type=block_type,
            has_children=data.get("has_children", False),
            archived=data.get("archived", False),
            created_time=created_time,
            last_edited_time=last_edited_time,
            content=content
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to Notion API format."""
        result = {
            "object": "block",
            "type": self.type,
            self.type: self.content or {}
        }
        return result
    
    @classmethod
    def paragraph(cls, text: Union[str, List[RichText]]) -> 'Block':
        """Create a paragraph block."""
        if isinstance(text, str):
            rich_text = [RichText.from_string(text).to_dict()]
        else:
            rich_text = [rt.to_dict() for rt in text]
        
        return cls(
            type="paragraph",
            content={"rich_text": rich_text}
        )
    
    @classmethod
    def heading_1(cls, text: Union[str, List[RichText]]) -> 'Block':
        """Create a heading 1 block."""
        if isinstance(text, str):
            rich_text = [RichText.from_string(text).to_dict()]
        else:
            rich_text = [rt.to_dict() for rt in text]
        
        return cls(
            type="heading_1",
            content={"rich_text": rich_text}
        )
    
    @classmethod
    def heading_2(cls, text: Union[str, List[RichText]]) -> 'Block':
        """Create a heading 2 block."""
        if isinstance(text, str):
            rich_text = [RichText.from_string(text).to_dict()]
        else:
            rich_text = [rt.to_dict() for rt in text]
        
        return cls(
            type="heading_2",
            content={"rich_text": rich_text}
        )
    
    @classmethod
    def bulleted_list_item(cls, text: Union[str, List[RichText]]) -> 'Block':
        """Create a bulleted list item block."""
        if isinstance(text, str):
            rich_text = [RichText.from_string(text).to_dict()]
        else:
            rich_text = [rt.to_dict() for rt in text]
        
        return cls(
            type="bulleted_list_item",
            content={"rich_text": rich_text}
        )
    
    @classmethod
    def numbered_list_item(cls, text: Union[str, List[RichText]]) -> 'Block':
        """Create a numbered list item block."""
        if isinstance(text, str):
            rich_text = [RichText.from_string(text).to_dict()]
        else:
            rich_text = [rt.to_dict() for rt in text]
        
        return cls(
            type="numbered_list_item",
            content={"rich_text": rich_text}
        )
    
    @classmethod
    def to_do(cls, text: Union[str, List[RichText]], checked: bool = False) -> 'Block':
        """Create a to-do block."""
        if isinstance(text, str):
            rich_text = [RichText.from_string(text).to_dict()]
        else:
            rich_text = [rt.to_dict() for rt in text]
        
        return cls(
            type="to_do",
            content={"rich_text": rich_text, "checked": checked}
        )
    
    @classmethod
    def code(cls, text: str, language: str = "plain text") -> 'Block':
        """Create a code block."""
        return cls(
            type="code",
            content={
                "rich_text": [RichText.from_string(text).to_dict()],
                "language": language
            }
        )


@dataclass
class SearchResult:
    """Represents a Notion search result."""
    results: List[Union[Page, Database]]
    has_more: bool = False
    next_cursor: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchResult':
        """Create SearchResult from Notion API response."""
        results = []
        for item in data.get("results", []):
            if item.get("object") == "page":
                results.append(Page.from_dict(item))
            elif item.get("object") == "database":
                results.append(Database.from_dict(item))
        
        return cls(
            results=results,
            has_more=data.get("has_more", False),
            next_cursor=data.get("next_cursor")
        )


@dataclass
class QueryResult:
    """Represents a database query result."""
    pages: List[Page]
    has_more: bool = False
    next_cursor: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QueryResult':
        """Create QueryResult from Notion API response."""
        pages = [Page.from_dict(item) for item in data.get("results", [])]
        
        return cls(
            pages=pages,
            has_more=data.get("has_more", False),
            next_cursor=data.get("next_cursor")
        )