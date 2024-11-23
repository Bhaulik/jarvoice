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
from base_models import Task, Reminder, ReminderCreate, TaskBase, TaskCreate, User, UserCreate
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
from outbound_caller import OutboundCaller
from twilio_sms import send_sms
# Load environment variables from .env.local
load_dotenv('.env.local')

app = FastAPI(
    title="Jarvoice API",
    description="Personal AI Assistant API that can manage tasks through phone calls & texts",
    version="1.0.0"
)
scheduler = SupabaseJobScheduler()
caller = OutboundCaller()

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

# Supabase client initialization
def get_supabase() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_ANON_KEY")
    if not url or not key:
        raise HTTPException(status_code=500, detail="Supabase credentials not configured")
    return create_client(url, key)

# Add new endpoints after your existing endpoints
@app.post("/users", response_model=User)
async def create_user(
    user: UserCreate,
    supabase: Client = Depends(get_supabase)
):
    try:
        response = supabase.table("users").insert(user.model_dump()).execute()
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to create user")
        return User(**response.data[0])
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/{user_id}", response_model=User)
async def get_user(
    user_id: UUID4,
    supabase: Client = Depends(get_supabase)
):
    try:
        response = supabase.table("users").select("*").eq("id", str(user_id)).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="User not found")
        return User(**response.data[0])
    except Exception as e:
        logger.error(f"Failed to get user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tasks", response_model=Task)
async def create_task(
    task: TaskCreate,
    supabase: Client = Depends(get_supabase)
):
    try:
        # Convert the model to a dict with datetime values as ISO format strings
        task_dict = {
            **task.model_dump(exclude_none=True),
            "created_at": datetime.now(pytz.UTC).isoformat(),
            "updated_at": datetime.now(pytz.UTC).isoformat(),
            "reminder_sent": False  # Add default value for reminder_sent
        }

        # Ensure datetime fields are converted to ISO format
        if task_dict.get('due_date'):
            task_dict['due_date'] = task_dict['due_date'].isoformat()
        if task_dict.get('reminder_time'):
            task_dict['reminder_time'] = task_dict['reminder_time'].isoformat()
        
        # Convert UUID to string
        task_dict['user_id'] = str(task_dict['user_id'])
        
        # Create task
        response = supabase.table("tasks").insert(task_dict).execute()
        
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to create task")
        
        created_task = Task(**response.data[0])

        # Schedule reminder if specified
        if task.reminder_time:
            try:
                # Get user's phone number
                user_response = supabase.table("users")\
                    .select("phone_number")\
                    .eq("id", str(task.user_id))\
                    .single()\
                    .execute()
                
                if user_response.data:
                    user_phone = user_response.data['phone_number']
                    reminder_message = f"Reminder: Your task '{created_task.title}' is due at {created_task.due_date.strftime('%I:%M %p')}"
                    
                    # Schedule both call and SMS reminders
                    scheduler.schedule_one_time_job(
                        func=caller.make_simple_call,
                        run_at=task.reminder_time,
                        job_id=f"task_reminder_call_{created_task.id}",
                        to_number=user_phone,
                        message=reminder_message,
                        metadata={
                            "task_id": str(created_task.id),
                            "user_id": str(task.user_id),
                            "reminder_type": "CALL"
                        }
                    )
                    
                    # Schedule SMS reminder (5 minutes after the call)
                    sms_reminder_time = task.reminder_time + timedelta(minutes=0)
                    scheduler.schedule_one_time_job(
                        func=send_sms,
                        run_at=sms_reminder_time,
                        job_id=f"task_reminder_sms_{created_task.id}",
                        to_number=user_phone,
                        message=reminder_message,
                        metadata={
                            "task_id": str(created_task.id),
                            "user_id": str(task.user_id),
                            "reminder_type": "SMS"
                        }
                    )
            except Exception as e:
                logger.error(f"Failed to schedule reminders: {e}")
                # Don't fail the task creation if reminder scheduling fails
                
        return created_task

    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tasks", response_model=List[Task])
async def get_tasks(
    supabase: Client = Depends(get_supabase),
    user_id: UUID4 = Query(...),
    status: Optional[str] = Query(None, regex="^(PENDING|IN_PROGRESS|COMPLETED|CANCELED)$"),
    due_after: Optional[datetime] = None,
    due_before: Optional[datetime] = None
):
    try:
        query = supabase.table("tasks").select("*").eq("user_id", str(user_id))
        
        if status:
            query = query.eq("status", status)
        if due_after:
            query = query.gte("due_date", due_after.isoformat())
        if due_before:
            query = query.lte("due_date", due_before.isoformat())
            
        response = query.execute()
        return [Task(**task_data) for task_data in response.data]

    except Exception as e:
        logger.error(f"Failed to fetch tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/tasks/{task_id}", response_model=Task)
async def update_task(
    task_id: UUID4,
    task_update: TaskBase,
    supabase: Client = Depends(get_supabase)
):
    try:
        # If reminder time is updated, reschedule the reminders
        if task_update.reminder_time:
            # Cancel existing reminder jobs if any
            scheduler.cancel_job(f"task_reminder_call_{task_id}")
            scheduler.cancel_job(f"task_reminder_sms_{task_id}")
            
            # Get user info for new reminders
            task_response = supabase.table("tasks").select("user_id").eq("id", str(task_id)).execute()
            if task_response.data:
                user_id = task_response.data[0]['user_id']
                user_response = supabase.table("users").select("phone_number").eq("id", user_id).execute()
                if user_response.data:
                    user_phone = user_response.data[0]['phone_number']
                    reminder_message = f"Reminder: Your task '{task_update.title}' is due soon"
                    
                    # Schedule new call reminder
                    scheduler.schedule_one_time_job(
                        func=caller.make_simple_call,
                        run_at=task_update.reminder_time,
                        job_id=f"task_reminder_call_{task_id}",
                        to_number=user_phone,
                        message=reminder_message,
                        metadata={
                            "task_id": str(task_id),
                            "user_id": user_id,
                            "reminder_type": "CALL"
                        }
                    )
                    
                    # Schedule new SMS reminder
                    sms_reminder_time = task_update.reminder_time + timedelta(minutes=5)
                    scheduler.schedule_one_time_job(
                        func=send_sms,
                        run_at=sms_reminder_time,
                        job_id=f"task_reminder_sms_{task_id}",
                        to_number=user_phone,
                        message=reminder_message,
                        metadata={
                            "task_id": str(task_id),
                            "user_id": user_id,
                            "reminder_type": "SMS"
                        }
                    )

        # Update task
        response = supabase.table("tasks").update(
            task_update.model_dump(exclude_unset=True)
        ).eq("id", str(task_id)).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Task not found")
            
        return Task(**response.data[0])

    except Exception as e:
        logger.error(f"Failed to update task: {e}")
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

@app.post("/test/call")
async def test_call():
    try:
        result = caller.make_simple_call(
            "+12045906645", 
            "Hello! This is a test message."
        )
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"Test call failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/test/schedule-call/{delay_seconds}")
async def schedule_test_call(delay_seconds: int = 20):
    try:
        # Schedule for specified seconds from now
        run_time = datetime.now(pytz.UTC) + timedelta(seconds=delay_seconds)
        
        # Separate metadata from function arguments
        metadata = {
            "scheduled_for": run_time.isoformat(),
            "job_type": "test_call"
        }
        
        # Function-specific arguments
        call_args = {
            "to_number": "+12045906645",  # Hardcoded test number
            "message": "Hello! This is a scheduled test call from your AI assistant."
        }
        
        job = scheduler.schedule_one_time_job(
            func=caller.make_simple_call,
            run_at=run_time,
            job_id=f"test_call_{datetime.now().timestamp()}",
            **call_args,  # Function arguments
            metadata=metadata  # Separate metadata
        )
        
        return {
            "message": "Test call scheduled successfully",
            "scheduled_time": run_time.isoformat(),
            "job_id": job.job_id,
            "delay_seconds": delay_seconds
        }
    except Exception as e:
        logger.error(f"Failed to schedule test call: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

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