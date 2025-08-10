"""
Data models for Google Calendar SDK.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any


@dataclass
class Calendar:
    """Represents a Google Calendar."""
    id: str
    summary: str
    description: Optional[str] = None
    location: Optional[str] = None
    time_zone: Optional[str] = None
    access_role: Optional[str] = None
    color_id: Optional[str] = None
    selected: bool = False
    primary: bool = False
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Calendar':
        """Create Calendar from Google Calendar API response."""
        return cls(
            id=data.get("id", ""),
            summary=data.get("summary", ""),
            description=data.get("description"),
            location=data.get("location"),
            time_zone=data.get("timeZone"),
            access_role=data.get("accessRole"),
            color_id=data.get("colorId"),
            selected=data.get("selected", False),
            primary=data.get("primary", False)
        )


@dataclass
class EventDateTime:
    """Represents event date/time."""
    date_time: Optional[datetime] = None
    date: Optional[str] = None
    time_zone: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EventDateTime':
        """Create EventDateTime from API response."""
        date_time = None
        if data.get("dateTime"):
            try:
                date_time = datetime.fromisoformat(data["dateTime"].replace('Z', '+00:00'))
            except ValueError:
                pass
        
        return cls(
            date_time=date_time,
            date=data.get("date"),
            time_zone=data.get("timeZone")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to Google Calendar API format."""
        result = {}
        if self.date_time:
            result["dateTime"] = self.date_time.isoformat()
        if self.date:
            result["date"] = self.date
        if self.time_zone:
            result["timeZone"] = self.time_zone
        return result


@dataclass
class EventAttendee:
    """Represents an event attendee."""
    email: str
    display_name: Optional[str] = None
    response_status: Optional[str] = None
    optional: bool = False
    organizer: bool = False
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EventAttendee':
        """Create EventAttendee from API response."""
        return cls(
            email=data.get("email", ""),
            display_name=data.get("displayName"),
            response_status=data.get("responseStatus"),
            optional=data.get("optional", False),
            organizer=data.get("organizer", False)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to Google Calendar API format."""
        result = {"email": self.email}
        if self.display_name:
            result["displayName"] = self.display_name
        if self.response_status:
            result["responseStatus"] = self.response_status
        if self.optional:
            result["optional"] = self.optional
        if self.organizer:
            result["organizer"] = self.organizer
        return result


@dataclass
class Event:
    """Represents a Google Calendar event."""
    id: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    start: Optional[EventDateTime] = None
    end: Optional[EventDateTime] = None
    attendees: Optional[List[EventAttendee]] = None
    created: Optional[datetime] = None
    updated: Optional[datetime] = None
    status: Optional[str] = None
    html_link: Optional[str] = None
    ical_uid: Optional[str] = None
    recurrence: Optional[List[str]] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create Event from Google Calendar API response."""
        # Parse attendees
        attendees = None
        if data.get("attendees"):
            attendees = [EventAttendee.from_dict(attendee) for attendee in data["attendees"]]
        
        # Parse start/end times
        start = EventDateTime.from_dict(data["start"]) if data.get("start") else None
        end = EventDateTime.from_dict(data["end"]) if data.get("end") else None
        
        # Parse created/updated times
        created = None
        if data.get("created"):
            try:
                created = datetime.fromisoformat(data["created"].replace('Z', '+00:00'))
            except ValueError:
                pass
        
        updated = None
        if data.get("updated"):
            try:
                updated = datetime.fromisoformat(data["updated"].replace('Z', '+00:00'))
            except ValueError:
                pass
        
        return cls(
            id=data.get("id"),
            summary=data.get("summary"),
            description=data.get("description"),
            location=data.get("location"),
            start=start,
            end=end,
            attendees=attendees,
            created=created,
            updated=updated,
            status=data.get("status"),
            html_link=data.get("htmlLink"),
            ical_uid=data.get("iCalUID"),
            recurrence=data.get("recurrence")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to Google Calendar API format."""
        result = {}
        
        if self.summary:
            result["summary"] = self.summary
        if self.description:
            result["description"] = self.description
        if self.location:
            result["location"] = self.location
        if self.start:
            result["start"] = self.start.to_dict()
        if self.end:
            result["end"] = self.end.to_dict()
        if self.attendees:
            result["attendees"] = [attendee.to_dict() for attendee in self.attendees]
        if self.recurrence:
            result["recurrence"] = self.recurrence
        
        return result