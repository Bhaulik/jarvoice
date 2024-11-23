from fastapi import FastAPI, APIRouter, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import datetime
from pydantic import UUID4, BaseModel
from supabase import create_client, Client
from fastapi import FastAPI, HTTPException, Query, Depends
from pathlib import Path
from dotenv import load_dotenv
from uuid import UUID

import os
from fastapi.middleware.cors import CORSMiddleware

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
    id: UUID4
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    attendees: List[str]
    status: str
    created_at: datetime
    updated_at: datetime

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)