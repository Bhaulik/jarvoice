from pydantic import BaseModel, UUID4, EmailStr, validator, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
import pytz
from enum import Enum
import json

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
    location: Optional[str] = None
    reminder_time: Optional[datetime] = None
    attendees: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    status: Optional[str] = None
    reminder_sent: Optional[bool] = None
    recurrence_rule: Optional[str] = None

    class Config:
        from_attributes = True

class EventCreate(BaseModel):
    title: str
    start_time: datetime
    end_time: datetime
    user_id: UUID4
    description: Optional[str] = None
    location: Optional[str] = None
    reminder_time: Optional[datetime] = None
    attendees: Optional[str] = None

    def model_dump(self, **kwargs):
        data = super().model_dump(**kwargs)
        # Convert all datetime fields to ISO format strings
        for field in ['start_time', 'end_time', 'reminder_time']:
            if data.get(field):
                data[field] = data[field].isoformat()
        # Convert UUID to string
        if data.get('user_id'):
            data['user_id'] = str(data['user_id'])
        # Convert attendees list to JSON string if present
        if data.get('attendees'):
            data['attendees'] = json.dumps(data['attendees'])
        return data

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