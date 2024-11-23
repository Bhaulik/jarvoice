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

import os
from fastapi.middleware.cors import CORSMiddleware
from cal import CalService

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

# Pydantic models
class Event(BaseModel):
    id: Optional[UUID4] = None
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    attendees: Optional[List[str]] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    calcom_event_id: Optional[str] = None
    updated_at: Optional[datetime] = None
    
    # Cal.com specific fields
    duration: Optional[int] = None  # lengthInMinutes
    slug: Optional[str] = None
    locations: Optional[List[Dict[str, Any]]] = None
    booking_fields: Optional[List[Dict[str, Any]]] = None
    disable_guests: Optional[bool] = None
    min_booking_notice: Optional[int] = None
    before_buffer: Optional[int] = None
    after_buffer: Optional[int] = None
    seats: Optional[Dict[str, Any]] = None
    hosts: Optional[List[Dict[str, Any]]] = None
    scheduling_type: Optional[Dict[str, Any]] = None
    custom_name: Optional[str] = None
    org_id: Optional[str] = None
    team_id: Optional[str] = None

    class Config:
        from_attributes = True

class EventResponse(BaseModel):
    data: List[Event]
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
        print(query)
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
            return EventResponse(
                data=[],
                count=0,
                page=page,
                page_size=page_size
            )

        # Transform the data to ensure proper typing
        events = []
        for event_data in response.data:
            # Ensure UUID fields are properly formatted
            event_data['id'] = UUID4(event_data['id'])
            
            # Ensure datetime fields are properly parsed
            event_data['start_time'] = datetime.fromisoformat(event_data['start_time'])
            event_data['end_time'] = datetime.fromisoformat(event_data['end_time'])
            event_data['created_at'] = datetime.fromisoformat(event_data['created_at'])
            event_data['updated_at'] = datetime.fromisoformat(event_data['updated_at'])
            
            # Ensure attendees is a list
            if 'attendees' not in event_data or event_data['attendees'] is None:
                event_data['attendees'] = []
                
            # Ensure status is a string
            if event_data['status'] is None:
                event_data['status'] = 'SCHEDULED'

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
    
@app.get("/events/{id}", response_model=Event)
async def get_event(
    id: UUID4,
    supabase: Client = Depends(get_supabase)
) -> Event:
    try:
        response = supabase.table("events").select("*").eq("id", str(id)).execute()
        
        if not response.data or len(response.data) == 0:
            raise HTTPException(status_code=404, detail="Event not found")

        event_data = response.data[0]
        return Event(
            id=UUID4(event_data['id']),
            title=event_data['title'],
            description=event_data['description'],
            start_time=datetime.fromisoformat(event_data['start_time']),
            end_time=datetime.fromisoformat(event_data['end_time']),
            attendees=event_data.get('attendees', []),
            status=event_data.get('status') or 'SCHEDULED',  # Default to 'SCHEDULED' if None
            created_at=datetime.fromisoformat(event_data['created_at']),
            updated_at=datetime.fromisoformat(event_data['updated_at'])
        )

    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))
    
# Update your event creation endpoint to sync with Cal.com
@app.post("/eventss", response_model=Event)
async def create_event(
    event: Event,
    background_tasks: BackgroundTasks,
    supabase: Client = Depends(get_supabase),
    cal_service: CalService = Depends(get_cal_service)
):
    try:
        # Convert Pydantic model to dict and format datetime fields
        event_dict = event.model_dump()
        event_dict['id'] = str(event_dict['id'])
        event_dict['start_time'] = event_dict['start_time'].isoformat()
        event_dict['end_time'] = event_dict['end_time'].isoformat()
        event_dict['created_at'] = event_dict['created_at'].isoformat()
        event_dict['updated_at'] = event_dict['updated_at'].isoformat()
        event_dict['calcom_event_id'] = 'pending'
        # Ensure status is uppercase
        event_dict['status'] = event_dict['status'].upper()
        
        # Save to Supabase
        response = supabase.table("events").insert(event_dict).execute()
        
        # Sync to Cal.com in the background
        background_tasks.add_task(cal_service.sync_event_to_cal, event_dict)
        
        return Event(**response.data[0])
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Add an endpoint to sync events from Cal.com
@app.post("/events/sync-from-cal")
async def sync_from_cal(
    supabase: Client = Depends(get_supabase),
    cal_service: CalService = Depends(get_cal_service)
):
    try:
        # Fetch events from Cal.com
        cal_events = await cal_service.get_cal_events()
        
        # Convert and save to Supabase
        for cal_event in cal_events:
            event_data = {
                "title": cal_event["title"],
                "description": cal_event.get("description"),
                "start_time": cal_event["startTime"],
                "end_time": cal_event["endTime"],
                "attendees": [attendee["email"] for attendee in cal_event.get("attendees", [])],
                "status": "SCHEDULED"
            }
            
            supabase.table("events").insert(event_data).execute()
            
        return {"message": "Events synced successfully", "count": len(cal_events)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)