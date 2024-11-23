from datetime import datetime, timedelta
import pytz
from typing import Optional, Union
from base_models import Task, Event, Reminder, ReminderCreate
from scheduler import scheduler
from outbound_caller import caller
from supabase import Client
import logging

logger = logging.getLogger(__name__)

class ReminderService:
    def __init__(self, supabase: Client):
        self.supabase = supabase
        self.caller = caller

    async def create_reminder(self, reminder: ReminderCreate) -> Reminder:
        try:
            response = self.supabase.table("reminders").insert(
                reminder.model_dump()
            ).execute()
            
            if not response.data:
                raise Exception("Failed to create reminder")
            
            return Reminder(**response.data[0])
        except Exception as e:
            logger.error(f"Failed to create reminder: {e}")
            raise

    async def schedule_reminder(
        self,
        entity: Union[Task, Event],
        user_phone: str,
        reminder_time: Optional[datetime] = None
    ):
        try:
            if not reminder_time:
                # Default to 1 hour before if not specified
                reminder_time = (
                    entity.due_date - timedelta(hours=1) 
                    if hasattr(entity, 'due_date') 
                    else entity.start_time - timedelta(hours=1)
                )

            # Create reminder message
            entity_type = "task" if isinstance(entity, Task) else "event"
            message = f"Reminder: Your {entity_type} '{entity.title}' is "
            
            if entity_type == "task":
                message += f"due at {entity.due_date.strftime('%I:%M %p')}"
            else:
                message += f"starting at {entity.start_time.strftime('%I:%M %p')}"

            # Create reminder record
            reminder = await self.create_reminder(
                ReminderCreate(
                    user_id=entity.user_id,
                    entity_type=entity_type.upper(),
                    entity_id=entity.id,
                    scheduled_time=reminder_time,
                    type='SMS',
                    message=message
                )
            )

            # Schedule the reminder
            job = scheduler.schedule_one_time_job(
                func=self._send_reminder,
                run_at=reminder_time,
                job_id=f"reminder_{reminder.id}",
                reminder_id=reminder.id,
                to_number=user_phone,
                message=message
            )

            return reminder, job

        except Exception as e:
            logger.error(f"Failed to schedule reminder: {e}")
            raise

    async def _send_reminder(self, reminder_id: str, to_number: str, message: str):
        try:
            # Send the SMS
            result = await self.caller.make_simple_call(to_number, message)
            
            # Update reminder status
            self.supabase.table("reminders").update({
                "status": "SENT" if result else "FAILED"
            }).eq("id", reminder_id).execute()
            
            return result
        except Exception as e:
            logger.error(f"Failed to send reminder {reminder_id}: {e}")
            self.supabase.table("reminders").update({
                "status": "FAILED"
            }).eq("id", reminder_id).execute()
            raise 