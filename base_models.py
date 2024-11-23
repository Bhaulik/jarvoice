from pydantic import BaseModel, UUID4, EmailStr, validator, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
import pytz
from enum import Enum

class UserBase(BaseModel):
    phone_number: str
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    timezone: str = 'UTC'
    notification_preferences: Dict[str, bool] = {"sms": True, "email": True}

    @validator('timezone')
    def validate_timezone(cls, v):
        if v not in pytz.all_timezones:
            raise ValueError('Invalid timezone')
        return v

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: UUID4
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class Event(BaseModel):
    id: UUID4
    user_id: UUID4
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: Literal['LOW', 'MEDIUM', 'HIGH'] = 'MEDIUM'
    status: Literal['PENDING', 'IN_PROGRESS', 'COMPLETED', 'CANCELED'] = 'PENDING'
    reminder_time: Optional[datetime] = None

class TaskCreate(TaskBase):
    user_id: UUID4
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID4: lambda v: str(v)
        }

class Task(TaskBase):
    id: UUID4
    user_id: UUID4
    reminder_sent: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ReminderBase(BaseModel):
    entity_type: Literal['TASK', 'EVENT']
    entity_id: UUID4
    scheduled_time: datetime
    type: Literal['SMS', 'EMAIL']
    message: str

class ReminderCreate(ReminderBase):
    user_id: UUID4

class Reminder(ReminderBase):
    id: UUID4
    status: Literal['PENDING', 'SENT', 'FAILED', 'CANCELED']
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ContactBase(BaseModel):
    name: str
    phone_number: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None

class ContactCreate(ContactBase):
    user_id: UUID4

class Contact(ContactBase):
    id: UUID4
    user_id: UUID4
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True 