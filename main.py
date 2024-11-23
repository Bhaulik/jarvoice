from fastapi import FastAPI, APIRouter, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import datetime, timedelta, time
from pydantic import UUID4, BaseModel
from supabase import create_client, Client
from fastapi import FastAPI, HTTPException, Query, Depends
from pathlib import Path
from dotenv import load_dotenv
from uuid import UUID

import os
from fastapi.middleware.cors import CORSMiddleware
from tool_functions import * 
import json
from fastapi import FastAPI, Request, HTTPException
from rich.table import Table
from rich.console import Console
from rich.panel import Panel
from rich import box
from tool_registry import ToolFunctionRegistry, console
import traceback
import uvicorn
import sys
import requests
from tool_registry import ArgumentType
import os
from vapi import Vapi
from typing import List, Dict, Any, Callable, TypeVar, Optional, Union, Type
from scheduler import schedule_event_reminder, cancel_event_reminder, shutdown_scheduler, SupabaseJobScheduler, TriggerType
import asyncio
import pytz

app = FastAPI(
    title="Jarvoice API",
    description="Personal AI Assistant API that can manage tasks through phone calls & texts",
    version="1.0.0"
)
scheduler = SupabaseJobScheduler()

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
    

@app.post("/1/process")
async def extract_tool_calls(request: Request):
    try:
        # Get raw body and parse JSON
        raw_body = await request.body()
        raw_json = json.loads(raw_body)
        
        # Extract customer phone number
        customer_number = raw_json.get('message', {}).get('customer', {}).get('number')
        logger.info(f"Customer phone number: {customer_number}")
        
        # Extract call information
        call_info = raw_json.get('message', {}).get('call', {})
        call_type = call_info.get('type')
        
        # Handle different call types and extract phone info
        phone_number = None
        if call_type == 'webCall':
            logger.info("Processing web call")
            # For web calls, use fallback number
            customer_number = '+12045906645'  # Fallback number for web calls
            logger.info(f"Using fallback number for web call: {customer_number}")
            # Web call URL logging remains the same
            web_call_url = call_info.get('webCallUrl')
            logger.info(f"Web call URL: {web_call_url}")
        else:
            # For regular calls, extract phone number (adjust path as needed)
            phone_number = call_info.get('phoneNumber')
            logger.info(f"Processing phone call from: {phone_number}")
        
        # Debug raw JSON structure
        # logger.info("=== Raw JSON Structure ===")
        # logger.info(json.dumps(raw_json, indent=2))
        
        # Extract message portion
        message_json = raw_json.get('message', {})
        # logger.info("=== Message JSON Structure ===")
        # logger.info(json.dumps(message_json, indent=2))
        
        # Check message type first
        message_type = message_json.get('type')
        # logger.info(f"=== Message Type: {message_type} ===")
        
        if message_type != 'tool-calls':
            logger.info(f"Message type is {message_type}, expected 'tool-calls'. Skipping processing.")
            return {"results": []}
        
        # If message type is correct, proceed with tool calls processing
        tool_calls = (
            message_json.get('toolCalls', []) or
            message_json.get('toolCallList', []) or
            message_json.get('toolWithToolCallList', [])
        )
        
        logger.info("=== Tool Calls Found ===")
        logger.info(json.dumps(tool_calls, indent=2))
        
        results = []
        
        if tool_calls:
            # Create a fancy table for logging
            results_table = Table(
                title="🛠️ Tool Function Execution Results 🛠️",
                show_header=True,
                header_style="bold magenta",
                border_style="cyan",
                box=box.DOUBLE
            )
            
            # Add columns
            results_table.add_column("Timestamp", style="cyan", no_wrap=True)
            results_table.add_column("Tool Call ID", style="green")
            results_table.add_column("Function", style="yellow")
            results_table.add_column("Status", style="bold blue")
            results_table.add_column("Result", style="white")

            for call in tool_calls:
                # Handle both direct tool calls and nested tool calls
                if 'toolCall' in call:
                    call = call['toolCall']
                
                call_id = call.get('id', 'unknown')
                function_data = call.get('function', {})
                function_name = function_data.get('name', 'unknown')
                
                # Extract and parse arguments
                args_raw = function_data.get('arguments', '{}')
                try:
                    args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
                    # Add customer_number to args if it exists
                    if customer_number:
                        args['customer_number'] = customer_number
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse arguments string: {args_raw}")
                    args = {'customer_number': customer_number} if customer_number else {}
                
                logger.info(f"Processing call: ID={call_id}, Function={function_name}, Arguments={args}")
                
                try:
                    result_text = ToolFunctionRegistry.execute(function_name, args)
                    status = "✅ SUCCESS"
                except Exception as e:
                    result_text = str(e)
                    status = "❌ FAILED"
                
                # Add row to table
                results_table.add_row(
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    str(call_id),
                    str(function_name),
                    str(status),
                    str(result_text)
                )
                
                results.append({
                    "toolCallId": call_id,
                    "result": result_text
                })
            
            # Print the fancy table
            console.print("\n")
            console.print(Panel(
                results_table,
                title="[bold yellow]Tool Execution Report[/bold yellow]",
                subtitle="[italic]Generated by FastAPI Service[/italic]",
                border_style="green"
            ))
            
            logger.info(f"Returning results: {results}")
            return {"results": results}
        
        logger.info("No tool calls found in any location")
        return {"results": []}

    except Exception as e:
        logger.error(f"Error in webhook: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="An error occurred while processing the request.")

# Modify the test function to properly use async/await
async def print_hello_world(**kwargs):
    """
    Async test function that prints Hello World and the current time
    """
    print('the weather is RAINY!!!')
    return "Hello World job completed successfully!!!!!!"

@app.post("/test/schedule-hello")
async def schedule_hello_world():
    try:
        # Schedule for 30 seconds from now
        run_time = datetime.now(pytz.UTC) + timedelta(seconds=20)
        
        metadata = {
            "test_data": "This is a test job",
            "scheduled_for": run_time.isoformat()
        }
        
        job = scheduler.schedule_one_time_job(
            func=print_hello_world,  # Using the async function
            run_at=run_time,
            job_id=f"hello_world_{datetime.now().timestamp()}",
            **metadata
        )
        
        return {
            "message": "Hello World job scheduled successfully",
            "scheduled_time": run_time.isoformat(),
            "job_id": job.job_id
        }
    except Exception as e:
        logger.error(f"Failed to schedule Hello World job: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Check the status of a scheduled job"""
    job = scheduler.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found"
        )
    
    return {
        "job_id": job.job_id,
        "status": job.status,
        "scheduled_for": job.run_date,
        "metadata": job.metadata
    }

if __name__ == "__main__":
    api_token = os.getenv("VAPI_TOKEN")
    if not api_token:
        logger.error("VAPI_TOKEN environment variable not set")
        sys.exit(1)
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    if not supabase_url or not supabase_key:
        logger.error("SUPABASE_URL or SUPABASE_ANON_KEY environment variable not set")
        sys.exit(1)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)