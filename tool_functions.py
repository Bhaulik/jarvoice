from dotenv import load_dotenv
import os
from tool_registry import ToolFunctionRegistry
from loguru import logger
from datetime import datetime, time
import uuid
import asyncio
from enum import Enum
from pydantic import BaseModel, Field
from loguru import logger
from typing import Dict, Any, List
import json
from datetime import datetime, timedelta
from supabase import create_client
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from twilio_sms import send_sms 

# Add at the very top of the file
load_dotenv()  # Load environment variables from .env file

# Debug line to verify variables are loaded
print("Supabase URL:", os.getenv("SUPABASE_URL"))
print("Supabase Key:", os.getenv("SUPABASE_ANON_KEY"))

# Add near the top of the file, before the functions
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_ANON_KEY")
)

# Initialize the scheduler
scheduler = AsyncIOScheduler()
scheduler.start()

# @ToolFunctionRegistry.register(
#     name="testFunction",
#     description="Test if the system is working properly",
#     arguments={
#         "customer_number": {
#             "type": "string",
#             "description": "Customer's phone number in E.164 format",
#             "required": False,
#             "pattern": "^\+[1-9]\d{1,14}$"
#         }
#     }
# )
# def test_function(customer_number: str = None) -> str:
#     """Test system functionality"""
#     print(f"This is a test function and the customer number is {customer_number}")
#     return "Test successful for bhaulik"

# @ToolFunctionRegistry.register(
#     name="abcfunction",
#     description="Adds two numbers together",
#     arguments={
#         "a": {
#             "type": "number",
#             "description": "First number to add",
#             "required": True
#         },
#         "b": {
#             "type": "number",
#             "description": "Second number to add",
#             "required": True
#         },
#                 "customer_number": {
#             "type": "string",
#             "description": "Customer's phone number in E.164 format",
#             "required": False,
#             "pattern": "^\+[1-9]\d{1,14}$"
#         }
#     }
# )
# def abcfunction(a, b, customer_number) -> str:
#     """Add two numbers together"""
#     logger.info(f"Adding numbers", a=a, b=b)
#     return "100 is the result"

@ToolFunctionRegistry.register(
    name="researchAndSchedule",
    description="Research a topic and schedule related tasks",
    arguments={
        "research_query": {
            "type": "string",
            "description": "Topic or question to research",
            "required": True
        },
        "schedule_task": {
            "type": "boolean",
            "description": "Whether to schedule follow-up tasks based on research",
            "required": False,
            "default": True
        },
        "customer_number": {
            "type": "string",
            "description": "Customer's phone number in E.164 format",
            "required": True,
            "pattern": "^\+[1-9]\d{1,14}$"
        }
    }
)
def research_and_schedule(research_query: str, schedule_task: bool = True, customer_number: str = None) -> str:
    """Research a topic and optionally schedule related tasks"""
    try:
        # Store the research query
        research_id = str(uuid.uuid4())
        research_data = {
            "id": research_id,
            "question": research_query,
            "answer": "Researching...",  # Will be updated async
            "user_id": customer_number,  # Using phone number as user_id for now
            "created_at": datetime.now().isoformat()
        }
        
        supabase.table('research_results').insert(research_data).execute()
        
        # Schedule the actual research to happen async
        scheduler.schedule_one_time_job(
            func=perform_research,
            run_at=datetime.now(),
            job_id=f"research_{research_id}",
            research_id=research_id,
            query=research_query
        )
        
        return f"Research initiated with ID: {research_id}. You'll receive results via SMS."
    except Exception as e:
        logger.error(f"Failed to initiate research: {str(e)}")
        return f"Failed to initiate research: {str(e)}"

@ToolFunctionRegistry.register(
    name="getResearchResults",
    description="Get recent research results or specific research by ID",
    arguments={
        "limit": {
            "type": "number",
            "description": "Number of recent research results to fetch (default: 3)",
            "required": False
        },
        "research_id": {
            "type": "string",
            "description": "ID of specific research to retrieve",
            "required": False
        },
        "customer_number": {
            "type": "string",
            "description": "Customer's phone number in E.164 format",
            "required": True,
            "pattern": "^\+[1-9]\d{1,14}$"
        }
    }
)
def get_research_results(limit: int = 3, research_id: str = None, customer_number: str = None) -> str:
    """Retrieve research results"""
    try:
        query = supabase.table('research_results')\
            .select('*')\
            .eq('user_id', customer_number)
            
        if research_id:
            query = query.eq('id', research_id)
        
        response = query.order('created_at', desc=True)\
            .limit(limit)\
            .execute()
            
        if not response.data:
            return "No research results found."
            
        results = []
        for r in response.data:
            created_at = datetime.fromisoformat(r['created_at']).strftime('%Y-%m-%d %H:%M')
            summary = f"📊 Research from {created_at}\n"
            summary += f"🔍 Query: {r['question']}\n"
            summary += f"💡 Answer: {r['answer'][:200]}..." if len(r['answer']) > 200 else f"💡 Answer: {r['answer']}"
            summary += f"\n🆔 ID: {r['id']}\n"
            results.append(summary)
            
        return "\n\n".join(results)
    except Exception as e:
        logger.error(f"Failed to retrieve research results: {str(e)}")
        return f"Failed to retrieve research results: {str(e)}"

@ToolFunctionRegistry.register(
    name="scheduleSmartReminder",
    description="Schedule a smart reminder with research-backed suggestions",
    arguments={
        "topic": {
            "type": "string",
            "description": "Topic or event to remind about",
            "required": True
        },
        "event_time": {
            "type": "string",
            "description": "Time of the event in ISO format",
            "required": True
        },
        "research_suggestions": {
            "type": "boolean",
            "description": "Whether to include researched suggestions",
            "required": False,
            "default": True
        },
        "customer_number": {
            "type": "string",
            "description": "Customer's phone number in E.164 format",
            "required": True,
            "pattern": "^\+[1-9]\d{1,14}$"
        }
    }
)
def schedule_smart_reminder(
    topic: str,
    event_time: str,
    research_suggestions: bool = True,
    customer_number: str = None
) -> str:
    """Schedule a smart reminder with context-aware suggestions"""
    try:
        event_datetime = datetime.fromisoformat(event_time)
        
        # Research relevant information if requested
        suggestions = ""
        if research_suggestions:
            research_query = f"Best practices and tips for: {topic}"
            research_id = str(uuid.uuid4())
            
            # Store research request
            supabase.table('research_results').insert({
                "id": research_id,
                "question": research_query,
                "user_id": customer_number,
                "created_at": datetime.now().isoformat()
            }).execute()
            
            # Schedule research processing
            scheduler.schedule_one_time_job(
                func=perform_research_and_send_suggestions,
                run_at=datetime.now(),
                job_id=f"smart_reminder_{research_id}",
                research_id=research_id,
                topic=topic,
                customer_number=customer_number,
                event_time=event_time
            )
            
        return f"Smart reminder scheduled for {event_datetime}. You'll receive preparation tips and suggestions via SMS."
    except Exception as e:
        logger.error(f"Failed to schedule smart reminder: {str(e)}")
        return f"Failed to schedule smart reminder: {str(e)}"

# Helper functions
async def perform_research(research_id: str, query: str) -> None:
    """Perform research using LangGraph and update results"""
    try:
        # Here you would integrate with your LangGraph research implementation
        # For now, we'll simulate research results
        research_result = f"Research findings for: {query}\n"
        research_result += "1. Key finding one\n"
        research_result += "2. Key finding two\n"
        research_result += "3. Recommendation"
        
        # Update research results in database
        supabase.table('research_results')\
            .update({"answer": research_result})\
            .eq('id', research_id)\
            .execute()
            
        # Get user contact and send notification
        research_data = supabase.table('research_results')\
            .select('user_id')\
            .eq('id', research_id)\
            .single()\
            .execute()
            
        if research_data.data:
            customer_number = research_data.data['user_id']
            send_sms(
                to_number=customer_number,
                message=f"Research results ready!\n\n{research_result[:160]}...\n\nReply 'MORE' to see full results."
            )
    except Exception as e:
        logger.error(f"Research failed: {str(e)}")

async def perform_research_and_send_suggestions(
    research_id: str,
    topic: str,
    customer_number: str,
    event_time: str
) -> None:
    """Perform research and send contextualized suggestions"""
    try:
        # Simulate research results for now
        suggestions = [
            f"Preparing for: {topic}",
            "1. Key preparation tip",
            "2. Important consideration",
            "3. Recommended action"
        ]
        
        # Schedule multiple informative messages
        event_datetime = datetime.fromisoformat(event_time)
        intervals = [
            timedelta(days=1),
            timedelta(hours=4),
            timedelta(hours=1),
            timedelta(minutes=30)
        ]
        
        for interval in intervals:
            send_time = event_datetime - interval
            if send_time > datetime.now():
                scheduler.schedule_notification(
                    recipient_id=customer_number,
                    message=f"Preparation tip for {topic}:\n{suggestions[intervals.index(interval)]}",
                    send_at=send_time,
                    notification_type="sms"
                )
    except Exception as e:
        logger.error(f"Failed to process research and suggestions: {str(e)}")

@ToolFunctionRegistry.register(
    name="createTask",
    description="Create a new task with optional reminder",
    arguments={
        "title": {
            "type": "string",
            "description": "Title of the task",
            "required": True
        },
        "description": {
            "type": "string",
            "description": "Detailed description of the task",
            "required": False
        },
        "due_date": {
            "type": "string",
            "description": "Due date in ISO format (YYYY-MM-DDTHH:MM:SS)",
            "required": True
        },
        "reminder_time": {
            "type": "string",
            "description": "When to send reminder in ISO format",
            "required": False
        },
        "customer_number": {
            "type": "string",
            "description": "Customer's phone number in E.164 format",
            "required": True,
            "pattern": "^\+[1-9]\d{1,14}$"
        }
    }
)
def create_task(title: str, due_date: str, customer_number: str, description: str = None, reminder_time: str = None) -> str:
    """Create a new task with optional reminder"""
    try:
        task_data = {
            "title": title,
            "description": description,
            "due_date": due_date,
            "reminder_time": reminder_time,
            "user_id": customer_number,  # Using phone number as user_id
            "status": "PENDING"
        }
        
        response = supabase.table("tasks").insert(task_data).execute()
        task = response.data[0]
        
        return f"✅ Task created: {title}\n📅 Due: {due_date}\n🔔 Reminder: {reminder_time or 'None'}"
    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        return f"Failed to create task: {str(e)}"

@ToolFunctionRegistry.register(
    name="getTasks",
    description="Get list of tasks for a user",
    arguments={
        "status": {
            "type": "string",
            "description": "Filter by status (PENDING/IN_PROGRESS/COMPLETED/CANCELED)",
            "required": False
        },
        "customer_number": {
            "type": "string",
            "description": "Customer's phone number in E.164 format",
            "required": True,
            "pattern": "^\+[1-9]\d{1,14}$"
        }
    }
)
def get_tasks(customer_number: str, status: str = None) -> str:
    """Get list of tasks for a user"""
    try:
        query = supabase.table("tasks").select("*").eq("user_id", customer_number)
        if status:
            query = query.eq("status", status)
        
        response = query.execute()
        
        if not response.data:
            return "No tasks found."
            
        tasks = []
        for task in response.data:
            status_emoji = {
                "PENDING": "⏳",
                "IN_PROGRESS": "🔄",
                "COMPLETED": "✅",
                "CANCELED": "❌"
            }.get(task['status'], "📝")
            
            task_summary = f"{status_emoji} {task['title']}\n"
            task_summary += f"📅 Due: {task['due_date']}\n"
            if task.get('description'):
                task_summary += f"📝 {task['description']}\n"
            tasks.append(task_summary)
            
        return "\n\n".join(tasks)
    except Exception as e:
        logger.error(f"Failed to get tasks: {e}")
        return f"Failed to get tasks: {str(e)}"

@ToolFunctionRegistry.register(
    name="createEvent",
    description="Create a new calendar event",
    arguments={
        "title": {
            "type": "string",
            "description": "Title of the event",
            "required": True
        },
        "start_time": {
            "type": "string",
            "description": "Start time in ISO format (YYYY-MM-DDTHH:MM:SS)",
            "required": True
        },
        "end_time": {
            "type": "string",
            "description": "End time in ISO format (YYYY-MM-DDTHH:MM:SS)",
            "required": True
        },
        "location": {
            "type": "string",
            "description": "Event location",
            "required": False
        },
        "reminder_minutes": {
            "type": "number",
            "description": "Minutes before event to send reminder (default: 30)",
            "required": False
        },
        "customer_number": {
            "type": "string",
            "description": "Customer's phone number in E.164 format",
            "required": True,
            "pattern": "^\+[1-9]\d{1,14}$"
        }
    }
)
def create_event(
    title: str,
    start_time: str,
    end_time: str,
    customer_number: str,
    location: str = None,
    reminder_minutes: int = 30
) -> str:
    """Create a new calendar event"""
    try:
        start_datetime = datetime.fromisoformat(start_time)
        reminder_time = start_datetime - timedelta(minutes=reminder_minutes)
        
        event_data = {
            "title": title,
            "start_time": start_time,
            "end_time": end_time,
            "location": location,
            "user_id": customer_number,
            "status": "SCHEDULED",
            "reminder_time": reminder_time.isoformat(),
            "reminder_sent": False
        }
        
        response = supabase.table("events").insert(event_data).execute()
        event = response.data[0]
        
        # Schedule reminder
        scheduler.schedule_one_time_job(
            func=send_event_reminder,
            run_at=reminder_time,
            job_id=f"event_reminder_{event['id']}",
            event_id=event['id']
        )
        
        return f"📅 Event created: {title}\n⏰ Start: {start_time}\n⌛ End: {end_time}\n📍 Location: {location or 'Not specified'}\n🔔 Reminder: {reminder_minutes} minutes before"
    except Exception as e:
        logger.error(f"Failed to create event: {e}")
        return f"Failed to create event: {str(e)}"

async def send_event_reminder(event_id: str) -> None:
    """Send reminder for an upcoming event"""
    try:
        event = supabase.table("events").select("*").eq("id", event_id).single().execute().data
        if event:
            message = f"🔔 Reminder: {event['title']} starts at {event['start_time']}"
            if event['location']:
                message += f"\n📍 Location: {event['location']}"
            
            send_sms(to_number=event['user_id'], message=message)
            
            # Update reminder status
            supabase.table("events").update({"reminder_sent": True}).eq("id", event_id).execute()
    except Exception as e:
        logger.error(f"Failed to send event reminder: {e}")
