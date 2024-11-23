from fastapi import FastAPI, APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import UUID4, BaseModel
from supabase import create_client, Client
from fastapi import FastAPI, HTTPException, Query, Depends
from pathlib import Path
from dotenv import load_dotenv
from uuid import UUID
from enum import Enum
import logging

import os
from fastapi.middleware.cors import CORSMiddleware
from cal import CalService, EventType, EventTypeCreate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Jarvoice API",
    description="Personal AI Assistant API that can manage tasks through phone calls & texts",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to Jarvoice API",
        "status": "active"
    }

class EventResponse(BaseModel):
    data: List[EventType]
    count: int
    page: int
    page_size: int

# Get the absolute path to your .env file
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path.resolve())

# Supabase client initialization
def get_supabase() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise HTTPException(status_code=500, detail="Supabase credentials not configured")
    return create_client(url, key)

# Add CalService dependency
def get_cal_service():
    return CalService()

@app.get("/events", response_model=EventResponse)
async def get_events(
    supabase: Client = Depends(get_supabase),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None, regex="^(SCHEDULED|CANCELED|COMPLETED)$"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    search: Optional[str] = None
):
    try:
        query = supabase.table("events").select("*", count="exact")
        # Apply filters
        if status:
            query = query.eq("status", status)
        if start_date:
            query = query.gte("start_time", start_date.isoformat())
        if end_date:
            query = query.lte("end_time", end_date.isoformat())
        if search:
            query = query.or_(f"title.ilike.%{search}%,description.ilike.%{search}%")

        # Calculate pagination
        offset = (page - 1) * page_size
        response = query.range(offset, offset + page_size - 1).execute()

        if not response.data:
            return EventResponse(data=[], count=0, page=page, page_size=page_size)

        # Transform the data to ensure proper typing
        events = []
        for event_data in response.data:
            # Handle required fields
            event_data['id'] = UUID4(event_data['id'])
            event_data['start_time'] = datetime.fromisoformat(event_data['start_time'])
            event_data['end_time'] = datetime.fromisoformat(event_data['end_time'])
            event_data['created_at'] = datetime.fromisoformat(event_data['created_at'])
            event_data['updated_at'] = datetime.fromisoformat(event_data['updated_at'])
            
            # Handle optional fields with defaults
            event_data['attendees'] = event_data.get('attendees', [])
            event_data['status'] = event_data.get('status', 'SCHEDULED')
            
            # Handle Cal.com specific fields
            event_data['duration'] = event_data.get('duration')
            event_data['duration_options'] = event_data.get('duration_options')
            event_data['slug'] = event_data.get('slug')
            event_data['locations'] = event_data.get('locations')
            event_data['booking_fields'] = event_data.get('booking_fields')
            event_data['disable_guests'] = event_data.get('disable_guests')
            event_data['slot_interval'] = event_data.get('slot_interval')
            event_data['min_booking_notice'] = event_data.get('min_booking_notice')
            event_data['before_buffer'] = event_data.get('before_buffer')
            event_data['after_buffer'] = event_data.get('after_buffer')
            event_data['booking_limits_count'] = event_data.get('booking_limits_count')
            event_data['booking_limits_duration'] = event_data.get('booking_limits_duration')
            event_data['booking_window'] = event_data.get('booking_window')
            event_data['offset_start'] = event_data.get('offset_start')
            event_data['booker_layouts'] = event_data.get('booker_layouts')
            event_data['confirmation_policy'] = event_data.get('confirmation_policy')
            event_data['recurrence'] = event_data.get('recurrence')
            event_data['requires_email_verification'] = event_data.get('requires_email_verification')
            event_data['hide_calendar_notes'] = event_data.get('hide_calendar_notes')
            event_data['lock_timezone'] = event_data.get('lock_timezone')
            event_data['color'] = event_data.get('color')
            event_data['seats'] = event_data.get('seats')
            event_data['custom_name'] = event_data.get('custom_name')
            event_data['destination_calendar'] = event_data.get('destination_calendar')
            event_data['use_destination_calendar_email'] = event_data.get('use_destination_calendar_email')
            event_data['hide_calendar_details'] = event_data.get('hide_calendar_details')
            event_data['org_id'] = event_data.get('org_id')
            event_data['team_id'] = event_data.get('team_id')

            events.append(Event(**event_data))

        return EventResponse(
            data=events,
            count=response.count,
            page=page,
            page_size=page_size
        )

    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/event-types/", response_model=EventTypeCreate, status_code=201)
async def create_event_type(
    event_type: EventTypeCreate,
    service: CalService = Depends(get_cal_service)
) -> EventType:
    """Create a new event type"""
    try:
        logger.info(f"Creating new event type: {event_type.title}")
        created_event = service.create_event_type(event_type)
        logger.info(f"Successfully created event type with ID: {created_event.id}")
        return created_event
    except Exception as e:
        logger.error(f"Error creating event type: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create event type: {str(e)}"
        )


# @app.get("/events/{id}", response_model=Event)
# async def get_event(
#     id: UUID4,
#     supabase: Client = Depends(get_supabase)
# ) -> Event:
#     try:
#         response = supabase.table("events").select("*").eq("id", str(id)).execute()
        
#         if not response.data or len(response.data) == 0:
#             raise HTTPException(status_code=404, detail="Event not found")

#         event_data = response.data[0]
        
#         # Transform the data
#         return Event(
#             # Required fields
#             id=UUID4(event_data['id']),
#             title=event_data['title'],
#             description=event_data['description'],
#             start_time=datetime.fromisoformat(event_data['start_time']),
#             end_time=datetime.fromisoformat(event_data['end_time']),
#             created_at=datetime.fromisoformat(event_data['created_at']),
#             updated_at=datetime.fromisoformat(event_data['updated_at']),
            
#             # Optional fields with defaults
#             attendees=event_data.get('attendees', []),
#             status=event_data.get('status', 'SCHEDULED'),
#             calcom_event_id=event_data.get('calcom_event_id'),
            
#             # Cal.com specific fields
#             duration=event_data.get('duration'),
#             duration_options=event_data.get('duration_options'),
#             slug=event_data.get('slug'),
#             locations=event_data.get('locations'),
#             booking_fields=event_data.get('booking_fields'),
#             disable_guests=event_data.get('disable_guests'),
#             slot_interval=event_data.get('slot_interval'),
#             min_booking_notice=event_data.get('min_booking_notice'),
#             before_buffer=event_data.get('before_buffer'),
#             after_buffer=event_data.get('after_buffer'),
#             booking_limits_count=event_data.get('booking_limits_count'),
#             booking_limits_duration=event_data.get('booking_limits_duration'),
#             booking_window=event_data.get('booking_window'),
#             offset_start=event_data.get('offset_start'),
#             booker_layouts=event_data.get('booker_layouts'),
#             confirmation_policy=event_data.get('confirmation_policy'),
#             recurrence=event_data.get('recurrence'),
#             requires_email_verification=event_data.get('requires_email_verification'),
#             hide_calendar_notes=event_data.get('hide_calendar_notes'),
#             lock_timezone=event_data.get('lock_timezone'),
#             color=event_data.get('color'),
#             seats=event_data.get('seats'),
#             custom_name=event_data.get('custom_name'),
#             destination_calendar=event_data.get('destination_calendar'),
#             use_destination_calendar_email=event_data.get('use_destination_calendar_email'),
#             hide_calendar_details=event_data.get('hide_calendar_details'),
#             org_id=event_data.get('org_id'),
#             team_id=event_data.get('team_id')
#         )

#     except Exception as e:
#         print(e)
#         raise HTTPException(status_code=500, detail=str(e))
    
# # Update your event creation endpoint to sync with Cal.com
# @app.post("/events", response_model=Event)
# async def create_event(
#     event: Event,
#     background_tasks: BackgroundTasks,
#     supabase: Client = Depends(get_supabase),
#     cal_service: CalService = Depends(get_cal_service)
# ):
#     try:
#         # Convert Pydantic model to dict and format datetime fields
#         event_dict = event.model_dump(exclude_none=True)  # Exclude None values
        
#         # Format datetime fields
#         datetime_fields = ['start_time', 'end_time', 'created_at', 'updated_at']
#         for field in datetime_fields:
#             if event_dict.get(field):
#                 event_dict[field] = event_dict[field].isoformat()
        
#         # Format UUID fields
#         if event_dict.get('id'):
#             event_dict['id'] = str(event_dict['id'])
            
#         # Set default values and validate required fields
#         event_dict.update({
#             'calcom_event_id': 'pending',
#             'status': event_dict.get('status', 'SCHEDULED').upper(),
#             'attendees': event_dict.get('attendees', []),
#             'duration': event_dict.get('duration', 60),
#             'duration_options': event_dict.get('duration_options', [15, 30, 60]),
#         })

#         # Handle Cal.com specific fields with defaults
#         cal_defaults = {
#             'slug': event_dict.get('slug', event_dict['title'].lower().replace(" ", "-")),
#             'locations': event_dict.get('locations', []),
#             'booking_fields': event_dict.get('booking_fields', []),
#             'disable_guests': event_dict.get('disable_guests', False),
#             'slot_interval': event_dict.get('slot_interval'),
#             'min_booking_notice': event_dict.get('min_booking_notice', 0),
#             'before_buffer': event_dict.get('before_buffer', 0),
#             'after_buffer': event_dict.get('after_buffer', 0),
#             'booking_limits_count': event_dict.get('booking_limits_count'),
#             'booking_limits_duration': event_dict.get('booking_limits_duration'),
#             'booking_window': event_dict.get('booking_window'),
#             'offset_start': event_dict.get('offset_start'),
#             'booker_layouts': event_dict.get('booker_layouts', {
#                 'defaultLayout': 'month',
#                 'enabledLayouts': ['month']
#             }),
#             'confirmation_policy': event_dict.get('confirmation_policy'),
#             'recurrence': event_dict.get('recurrence'),
#             'requires_email_verification': event_dict.get('requires_email_verification', False),
#             'hide_calendar_notes': event_dict.get('hide_calendar_notes', False),
#             'lock_timezone': event_dict.get('lock_timezone', False),
#             'color': event_dict.get('color'),
#             'seats': event_dict.get('seats'),
#             'custom_name': event_dict.get('custom_name'),
#             'destination_calendar': event_dict.get('destination_calendar'),
#             'use_destination_calendar_email': event_dict.get('use_destination_calendar_email', False),
#             'hide_calendar_details': event_dict.get('hide_calendar_details', False)
#         }
        
#         # Update event_dict with Cal.com defaults
#         event_dict.update({k: v for k, v in cal_defaults.items() if v is not None})
        
#         # Validate required fields for Cal.com sync
#         if event_dict.get('org_id') and event_dict.get('team_id'):
#             if not event_dict.get('title'):
#                 raise HTTPException(status_code=400, detail="Title is required for Cal.com sync")
#             if not event_dict.get('description'):
#                 raise HTTPException(status_code=400, detail="Description is required for Cal.com sync")
        
#         # Save to Supabase
#         response = supabase.table("events").insert(event_dict).execute()
        
#         if not response.data:
#             raise HTTPException(status_code=500, detail="Failed to create event in database")
        
#         created_event = response.data[0]
        
#         # Sync to Cal.com in the background if org_id and team_id are provided
#         if event_dict.get('org_id') and event_dict.get('team_id'):
#             background_tasks.add_task(cal_service.sync_event_to_cal, event_dict)
        
#         # Transform datetime strings back to datetime objects for response
#         for field in datetime_fields:
#             if created_event.get(field):
#                 created_event[field] = datetime.fromisoformat(created_event[field])
        
#         # Transform UUID string back to UUID object
#         if created_event.get('id'):
#             created_event['id'] = UUID4(created_event['id'])
        
#         return Event(**created_event)
        
#     except Exception as e:
#         print(f"Error creating event: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

# Add an endpoint to sync events from Cal.com
@app.post("/events/sync-from-cal")
async def sync_from_cal(
    supabase: Client = Depends(get_supabase),
    cal_service: CalService = Depends(get_cal_service)
):
    try:
        cal_events = await cal_service.get_cal_events()
        
        for cal_event in cal_events:
            event_data = {
                "title": cal_event["title"],
                "description": cal_event.get("description"),
                "start_time": cal_event["startTime"],
                "end_time": cal_event["endTime"],
                "attendees": [attendee["email"] for attendee in cal_event.get("attendees", [])],
                "status": "SCHEDULED",
                # Cal.com specific fields
                "duration": cal_event.get("lengthInMinutes"),
                "duration_options": cal_event.get("lengthInMinutesOptions"),
                "slug": cal_event.get("slug"),
                "locations": cal_event.get("locations"),
                "booking_fields": cal_event.get("bookingFields"),
                "disable_guests": cal_event.get("disableGuests"),
                "slot_interval": cal_event.get("slotInterval"),
                "min_booking_notice": cal_event.get("minimumBookingNotice"),
                "before_buffer": cal_event.get("beforeEventBuffer"),
                "after_buffer": cal_event.get("afterEventBuffer"),
                "booking_limits_count": cal_event.get("bookingLimitsCount"),
                "booking_limits_duration": cal_event.get("bookingLimitsDuration"),
                "booking_window": cal_event.get("bookingWindow"),
                "offset_start": cal_event.get("offsetStart"),
                "booker_layouts": cal_event.get("bookerLayouts"),
                "confirmation_policy": cal_event.get("confirmationPolicy"),
                "recurrence": cal_event.get("recurrence"),
                "requires_email_verification": cal_event.get("requiresBookerEmailVerification"),
                "hide_calendar_notes": cal_event.get("hideCalendarNotes"),
                "lock_timezone": cal_event.get("lockTimeZoneToggleOnBookingPage"),
                "color": cal_event.get("color"),
                "seats": cal_event.get("seats"),
                "custom_name": cal_event.get("customName"),
                "destination_calendar": cal_event.get("destinationCalendar"),
                "use_destination_calendar_email": cal_event.get("useDestinationCalendarEmail"),
                "hide_calendar_details": cal_event.get("hideCalendarEventDetails"),
                "calcom_event_id": cal_event.get("id")
            }
            
            # Remove None values
            event_data = {k: v for k, v in event_data.items() if v is not None}
            
            supabase.table("events").insert(event_data).execute()
            
        return {"message": "Events synced successfully", "count": len(cal_events)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)