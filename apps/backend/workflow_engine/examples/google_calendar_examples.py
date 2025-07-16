"""
Google Calendar API client usage examples.

This module demonstrates how to use the GoogleCalendarClient for various
calendar operations including event management, calendar listing, and
free/busy queries.
"""

import asyncio
from datetime import datetime, timedelta
from workflow_engine.clients.google_calendar_client import GoogleCalendarClient
from workflow_engine.models.credential import OAuth2Credential


async def example_basic_operations():
    """Demonstrate basic Google Calendar operations."""
    
    # Create OAuth2 credentials (normally obtained through OAuth flow)
    credentials = OAuth2Credential(
        access_token="your_access_token",
        refresh_token="your_refresh_token",
        token_type="Bearer",
        expires_at=datetime.utcnow() + timedelta(hours=1),
        provider="google_calendar"
    )
    
    # Initialize the client
    client = GoogleCalendarClient(credentials)
    
    try:
        print("=== Google Calendar API Examples ===\n")
        
        # 1. List available calendars
        print("1. Listing available calendars...")
        calendars = await client.list_calendars()
        for calendar in calendars:
            print(f"  - {calendar['summary']} (ID: {calendar['id']})")
        print()
        
        # 2. Create a new event
        print("2. Creating a new event...")
        event_data = {
            "summary": "Team Meeting",
            "description": "Weekly team sync meeting",
            "start": {
                "dateTime": "2025-01-22T10:00:00Z",
                "timeZone": "UTC"
            },
            "end": {
                "dateTime": "2025-01-22T11:00:00Z",
                "timeZone": "UTC"
            },
            "attendees": [
                {"email": "team-member@example.com"},
                {"email": "manager@example.com"}
            ],
            "location": "Conference Room A"
        }
        
        created_event = await client.create_event("primary", event_data)
        event_id = created_event["id"]
        print(f"  Created event: {created_event['summary']} (ID: {event_id})")
        print(f"  Event link: {created_event.get('htmlLink', 'N/A')}")
        print()
        
        # 3. List events in a time range
        print("3. Listing events for the next 7 days...")
        time_min = datetime.utcnow().isoformat() + "Z"
        time_max = (datetime.utcnow() + timedelta(days=7)).isoformat() + "Z"
        
        events_response = await client.list_events(
            "primary",
            time_min=time_min,
            time_max=time_max,
            max_results=10
        )
        
        print(f"  Found {len(events_response.items)} events:")
        for event in events_response.items:
            start_time = event.get("start", {}).get("dateTime", "All day")
            print(f"  - {event.get('summary', 'No title')} at {start_time}")
        print()
        
        # 4. Get specific event details
        print("4. Getting event details...")
        event_details = await client.get_event("primary", event_id)
        print(f"  Event: {event_details['summary']}")
        print(f"  Start: {event_details['start']['dateTime']}")
        print(f"  End: {event_details['end']['dateTime']}")
        print(f"  Attendees: {len(event_details.get('attendees', []))}")
        print()
        
        # 5. Update the event
        print("5. Updating the event...")
        update_data = {
            "summary": "Team Meeting - Updated",
            "description": "Weekly team sync meeting - now with updated agenda",
            "location": "Conference Room B"
        }
        
        updated_event = await client.update_event("primary", event_id, update_data)
        print(f"  Updated event: {updated_event['summary']}")
        print(f"  New location: {updated_event.get('location', 'N/A')}")
        print()
        
        # 6. Quick add event using natural language
        print("6. Quick adding an event...")
        quick_event = await client.quick_add_event(
            "primary", 
            "Lunch with John tomorrow at 12:30pm"
        )
        quick_event_id = quick_event["id"]
        print(f"  Quick added: {quick_event['summary']}")
        print()
        
        # 7. Check free/busy information
        print("7. Checking free/busy information...")
        free_busy = await client.get_free_busy(
            ["primary"],
            time_min,
            time_max
        )
        
        busy_times = free_busy.get("calendars", {}).get("primary", {}).get("busy", [])
        print(f"  Found {len(busy_times)} busy periods in the next 7 days")
        for busy_time in busy_times[:3]:  # Show first 3
            print(f"  - Busy: {busy_time['start']} to {busy_time['end']}")
        print()
        
        # 8. Delete the events (cleanup)
        print("8. Cleaning up - deleting created events...")
        await client.delete_event("primary", event_id)
        print(f"  Deleted event: {event_id}")
        
        await client.delete_event("primary", quick_event_id)
        print(f"  Deleted quick event: {quick_event_id}")
        print()
        
        print("✅ All examples completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        # Always close the client
        await client.close()


async def example_event_management():
    """Demonstrate advanced event management features."""
    
    credentials = OAuth2Credential(
        access_token="your_access_token",
        refresh_token="your_refresh_token", 
        token_type="Bearer",
        expires_at=datetime.utcnow() + timedelta(hours=1),
        provider="google_calendar"
    )
    
    client = GoogleCalendarClient(credentials)
    
    try:
        print("=== Advanced Event Management Examples ===\n")
        
        # Create all-day event
        print("1. Creating an all-day event...")
        all_day_event = {
            "summary": "Company Holiday",
            "description": "Annual company holiday",
            "start": {
                "date": "2025-01-25"
            },
            "end": {
                "date": "2025-01-26"
            }
        }
        
        created_all_day = await client.create_event("primary", all_day_event)
        print(f"  Created all-day event: {created_all_day['summary']}")
        
        # Create recurring event pattern
        print("\n2. Creating a recurring event...")
        recurring_event = {
            "summary": "Daily Standup",
            "description": "Daily team standup meeting",
            "start": {
                "dateTime": "2025-01-21T09:00:00Z",
                "timeZone": "UTC"
            },
            "end": {
                "dateTime": "2025-01-21T09:30:00Z",
                "timeZone": "UTC"
            },
            "recurrence": [
                "RRULE:FREQ=DAILY;COUNT=5"  # Daily for 5 days
            ],
            "attendees": [
                {"email": "dev-team@example.com"}
            ]
        }
        
        created_recurring = await client.create_event("primary", recurring_event)
        print(f"  Created recurring event: {created_recurring['summary']}")
        
        # Event with reminders
        print("\n3. Creating event with custom reminders...")
        event_with_reminders = {
            "summary": "Important Meeting",
            "description": "Meeting with important stakeholders",
            "start": {
                "dateTime": "2025-01-23T14:00:00Z",
                "timeZone": "UTC"
            },
            "end": {
                "dateTime": "2025-01-23T15:00:00Z",
                "timeZone": "UTC"
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 24 * 60},  # 1 day before
                    {"method": "popup", "minutes": 30}       # 30 minutes before
                ]
            }
        }
        
        created_with_reminders = await client.create_event("primary", event_with_reminders)
        print(f"  Created event with reminders: {created_with_reminders['summary']}")
        
        # Pagination example
        print("\n4. Demonstrating pagination...")
        page_token = None
        total_events = 0
        page_num = 1
        
        while page_num <= 2:  # Limit to 2 pages for demo
            events_page = await client.list_events(
                "primary",
                max_results=5,
                page_token=page_token
            )
            
            print(f"  Page {page_num}: {len(events_page.items)} events")
            total_events += len(events_page.items)
            
            if not events_page.has_more:
                break
                
            page_token = events_page.next_page_token
            page_num += 1
        
        print(f"  Total events found: {total_events}")
        
        # Cleanup
        print("\n5. Cleaning up created events...")
        for event_id in [
            created_all_day["id"],
            created_recurring["id"],
            created_with_reminders["id"]
        ]:
            try:
                await client.delete_event("primary", event_id)
                print(f"  Deleted event: {event_id}")
            except Exception as e:
                print(f"  Failed to delete {event_id}: {e}")
        
        print("\n✅ Advanced examples completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        await client.close()


async def example_error_handling():
    """Demonstrate error handling patterns."""
    
    credentials = OAuth2Credential(
        access_token="your_access_token",
        refresh_token="your_refresh_token",
        token_type="Bearer", 
        expires_at=datetime.utcnow() + timedelta(hours=1),
        provider="google_calendar"
    )
    
    client = GoogleCalendarClient(credentials)
    
    try:
        print("=== Error Handling Examples ===\n")
        
        # 1. Handle calendar not found
        print("1. Testing calendar not found error...")
        try:
            await client.list_events("nonexistent_calendar")
        except Exception as e:
            print(f"  Caught expected error: {type(e).__name__}: {e}")
        
        # 2. Handle event not found
        print("\n2. Testing event not found error...")
        try:
            await client.get_event("primary", "nonexistent_event")
        except Exception as e:
            print(f"  Caught expected error: {type(e).__name__}: {e}")
        
        # 3. Handle validation errors
        print("\n3. Testing validation errors...")
        try:
            invalid_event = {
                "description": "Event without required fields"
                # Missing summary, start, end
            }
            await client.create_event("primary", invalid_event)
        except ValueError as e:
            print(f"  Caught validation error: {e}")
        
        # 4. Handle invalid attendee format
        print("\n4. Testing invalid attendee format...")
        try:
            invalid_attendees_event = {
                "summary": "Test Event",
                "start": {"dateTime": "2025-01-22T10:00:00Z"},
                "end": {"dateTime": "2025-01-22T11:00:00Z"},
                "attendees": [{"name": "No Email Field"}]  # Missing email
            }
            await client.create_event("primary", invalid_attendees_event)
        except ValueError as e:
            print(f"  Caught attendee validation error: {e}")
        
        print("\n✅ Error handling examples completed!")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    finally:
        await client.close()


async def main():
    """Run all examples."""
    print("🚀 Starting Google Calendar API Client Examples\n")
    
    # Note: To run these examples with real Google Calendar API:
    # 1. Set up Google Cloud project and enable Calendar API
    # 2. Create OAuth2 credentials
    # 3. Complete OAuth2 authorization flow to get access/refresh tokens
    # 4. Replace the example credentials with real tokens
    
    print("⚠️  Note: These examples use placeholder credentials.")
    print("   To run with real Google Calendar API, replace with actual OAuth2 tokens.\n")
    
    try:
        # Basic operations examples
        await example_basic_operations()
        print("\n" + "="*60 + "\n")
        
        # Advanced event management
        await example_event_management()
        print("\n" + "="*60 + "\n")
        
        # Error handling patterns
        await example_error_handling()
        
    except Exception as e:
        print(f"❌ Examples failed: {e}")
    
    print("\n🎉 All examples completed!")


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main()) 