from uuid import UUID
import requests
from datetime import datetime
from typing import Dict, Any, List
import os
from pydantic import BaseModel, UUID4, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class LocationType(str, Enum):
    GOOGLEMEET = "googlemeet"
    ZOOM = "zoom"
    TEAMS = "teamsMeeting"
    ADDRESS = "address"

class EventStatus(str, Enum):
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    PENDING = "pending"

class Location(BaseModel):
    type: LocationType
    address: Optional[str] = None
    public: bool = True

class BookingField(BaseModel):
    type: str
    slug: str
    label: str
    required: bool = False
    placeholder: Optional[str] = None
    disableOnPrefill: bool = False

class BookingLimits(BaseModel):
    day: Optional[int] = None
    week: Optional[int] = None
    month: Optional[int] = None
    year: Optional[int] = None

class BookingWindow(BaseModel):
    type: str
    value: Optional[int] = None
    rolling: bool = True

class ConfirmationPolicy(BaseModel):
    type: str = "always"
    noticeThreshold: Dict[str, Any]

class Recurrence(BaseModel):
    interval: Optional[int] = None
    occurrences: Optional[int] = None
    frequency: Optional[str] = None

class Seats(BaseModel):
    seatsPerTimeSlot: Optional[int] = None
    showAttendeeInfo: bool = False
    showAvailabilityCount: bool = False

class Color(BaseModel):
    lightThemeHex: str = "#292929"
    darkThemeHex: str = "#fafafa"

class DestinationCalendar(BaseModel):
    integration: Optional[str] = None
    externalId: Optional[str] = None

class BookerLayouts(BaseModel):
    defaultLayout: str = "month"
    enabledLayouts: List[str] = ["month"]

class EventType(BaseModel):
    # Primary identification
    id: Optional[UUID4] = None
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    
    # Basic event settings
    title: str
    slug: Optional[str] = None
    description: Optional[str] = None
    length_in_minutes: int = 60
    length_in_minutes_options: List[int] = [15, 30, 60]
    
    # Location and booking settings
    locations: Optional[List[Location]] = None
    booking_fields: Optional[List[BookingField]] = None
    disable_guests: bool = False
    
    # Time settings
    slot_interval: Optional[int] = None
    minimum_booking_notice: Optional[int] = None
    before_event_buffer: Optional[int] = None
    after_event_buffer: Optional[int] = None
    schedule_id: Optional[int] = None
    
    # Booking limits
    booking_limits_count: Optional[BookingLimits] = None
    only_show_first_available_slot: bool = False
    booking_limits_duration: Optional[BookingLimits] = None
    booking_window: Optional[BookingWindow] = None
    offset_start: Optional[int] = None
    
    # Layout and display settings
    booker_layouts: BookerLayouts = Field(default_factory=BookerLayouts)
    confirmation_policy: Optional[ConfirmationPolicy] = None
    recurrence: Optional[Recurrence] = None
    
    # Additional settings
    requires_booker_email_verification: bool = False
    hide_calendar_notes: bool = False
    lock_timezone_toggle_on_booking_page: bool = False
    color: Optional[Color] = None
    seats: Optional[Seats] = None
    custom_name: Optional[str] = None
    
    # Calendar settings
    destination_calendar: Optional[DestinationCalendar] = None
    use_destination_calendar_email: bool = False
    hide_calendar_event_details: bool = False
    
    # Organization and user settings
    owner_id: Optional[int] = None
    org_id: Optional[UUID4] = None
    team_id: Optional[UUID4] = None
    users: Optional[List[str]] = None
    
    # Booking and status
    status: Optional[EventStatus] = EventStatus.PENDING
    attendees: Optional[List[str]] = None
    calcom_event_id: Optional[str] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID4: lambda v: str(v)
        }
        
    @validator('slug', pre=True, always=True)
    def generate_slug(cls, v, values):
        if v is None and 'title' in values:
            # Convert title to lowercase, replace spaces with hyphens
            # and remove special characters
            import re
            slug = values['title'].lower()
            slug = re.sub(r'[^\w\s-]', '', slug)
            slug = re.sub(r'[-\s]+', '-', slug)
            return slug.strip('-')
        return v

    @validator('updated_at', pre=True, always=True)
    def set_updated_at(cls, v, values, **kwargs):
        return datetime.utcnow()

class EventTypeCreate(EventType):
    title: str
    description: str
    length_in_minutes: int = 60

class EventTypeUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    length_in_minutes: Optional[int] = None
    length_in_minutes_options: Optional[List[int]] = None
    locations: Optional[List[Location]] = None
    booking_fields: Optional[List[BookingField]] = None
    disable_guests: Optional[bool] = None
    slot_interval: Optional[int] = None
    minimum_booking_notice: Optional[int] = None
    before_event_buffer: Optional[int] = None
    after_event_buffer: Optional[int] = None
    schedule_id: Optional[int] = None
    booking_limits_count: Optional[BookingLimits] = None
    booking_limits_duration: Optional[BookingLimits] = None
    booking_window: Optional[BookingWindow] = None
    status: Optional[EventStatus] = None

    class Config:
        from_attributes = True

class EventTypeResponse(EventType):
    id: UUID4
    created_at: datetime
    updated_at: datetime

class CalService:
    def __init__(self):
        self.base_url = f"https://api.cal.com/v2/"
        self.api_url = os.environ.get("CAL_API_URL")
        self.headers = {
            "Authorization": f"Bearer {os.environ.get('CAL_API_KEY')}",
            "Content-Type": "application/json"
        }

    def _handle_response(self, response: requests.Response) -> Dict:
        """Handle API response and raise appropriate exceptions"""
        try:
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_msg = f"Cal.com API error: {response.text}"
            raise Exception(error_msg) from e
        except Exception as e:
            raise Exception(f"Unexpected error: {str(e)}") from e

    def create_event_type(self, event_type: EventTypeCreate) -> EventType:
        """Create a new event type"""
        payload = {
            "title": event_type.title,
            "slug": event_type.slug,
            "length": event_type.length_in_minutes,
            "description": event_type.description,
            "locations": [loc.dict() for loc in (event_type.locations or [])],
            "bookingFields": [field.dict() for field in (event_type.booking_fields or [])],
            "disableGuests": event_type.disable_guests,
            "slotInterval": event_type.slot_interval,
            "minimumBookingNotice": event_type.minimum_booking_notice,
            "beforeEventBuffer": event_type.before_event_buffer,
            "afterEventBuffer": event_type.after_event_buffer,
            "scheduleId": event_type.schedule_id,
            "bookingLimitsCount": event_type.booking_limits_count.dict() if event_type.booking_limits_count else None,
            "onlyShowFirstAvailableSlot": event_type.only_show_first_available_slot,
            "bookingLimitsDuration": event_type.booking_limits_duration.dict() if event_type.booking_limits_duration else None,
            "bookingWindow": event_type.booking_window.dict() if event_type.booking_window else None,
            "offsetStart": event_type.offset_start,
            "bookerLayouts": event_type.booker_layouts.dict(),
            "confirmationPolicy": event_type.confirmation_policy.dict() if event_type.confirmation_policy else None,
            "recurrence": event_type.recurrence.dict() if event_type.recurrence else None,
            "requiresBookerEmailVerification": event_type.requires_booker_email_verification,
            "hideCalendarNotes": event_type.hide_calendar_notes,
            "lockTimeZoneToggleOnBookingPage": event_type.lock_timezone_toggle_on_booking_page,
            "color": event_type.color.dict() if event_type.color else None,
            "seats": event_type.seats.dict() if event_type.seats else None,
            "customName": event_type.custom_name,
            "destinationCalendar": event_type.destination_calendar.dict() if event_type.destination_calendar else None,
            "useDestinationCalendarEmail": event_type.use_destination_calendar_email,
            "hideCalendarEventDetails": event_type.hide_calendar_event_details
        }

        response = requests.post(
            self.base_url+'event-types',
            json={k: v for k, v in payload.items() if v is not None},
            headers=self.headers
        )
        
        data = self._handle_response(response)
        
        # Extract the event type data from the response
        if isinstance(data, dict) and 'data' in data:
            event_data = data['data']
        else:
            event_data = data
        
        # Ensure required fields are present
        event_data['title'] = event_type.title  # Use the original title if not in response
        event_data['status'] = EventStatus.PENDING  # Set default status if not provided
        
        return EventType.parse_obj(event_data)

    def get_event_type(self, event_type_id: UUID) -> EventType:
        """Retrieve an event type by ID"""
        response = requests.get(
            f"{self.base_url}/{event_type_id}",
            headers=self.headers
        )
        data = self._handle_response(response)
        return EventType.parse_obj(data)

    def update_event_type(self, event_type_id: UUID, update_data: EventTypeUpdate) -> EventType:
        """Update an existing event type"""
        payload = update_data.dict(exclude_unset=True)
        response = requests.patch(
            f"{self.base_url}/{event_type_id}",
            json=payload,
            headers=self.headers
        )
        data = self._handle_response(response)
        return EventType.parse_obj(data)

    def delete_event_type(self, event_type_id: UUID) -> bool:
        """Delete an event type"""
        response = requests.delete(
            f"{self.base_url}/{event_type_id}",
            headers=self.headers
        )
        self._handle_response(response)
        return True

    def list_event_types(self, limit: int = 100, offset: int = 0) -> List[EventType]:
        """List all event types with pagination"""
        params = {
            "limit": limit,
            "offset": offset
        }
        response = requests.get(
            self.base_url,
            params=params,
            headers=self.headers
        )
        data = self._handle_response(response)
        return [EventType.parse_obj(item) for item in data.get("items", [])]


