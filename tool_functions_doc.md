Tool Functions Documentation

https://4d40-2601-645-8780-dc0-707e-6f61-af14-d1.ngrok-free.app/1/process

2. researchAndSchedule
Research a topic and schedule related tasks.
Parameters:
research_query (string) - Topic or question to research
schedule_task (boolean, optional) - Whether to schedule follow-up tasks based on research (default: True)
customer_number (string) - Customer's phone number in E.164 format (pattern: ^\+[1-9]\d{1,14}$)
3. getResearchResults
Get recent research results or specific research by ID.
Parameters:
limit (number, optional) - Number of recent research results to fetch (default: 3)
research_id (string, optional) - ID of specific research to retrieve
customer_number (string) - Customer's phone number in E.164 format (pattern: ^\+[1-9]\d{1,14}$)
4. scheduleSmartReminder
Schedule a smart reminder with research-backed suggestions.
Parameters:
topic (string) - Topic or event to remind about
event_time (string) - Time of the event in ISO format
research_suggestions (boolean, optional) - Whether to include researched suggestions (default: True)
customer_number (string) - Customer's phone number in E.164 format (pattern: ^\+[1-9]\d{1,14}$)
5. createTask
Create a new task with optional reminder.
Parameters:
title (string) - Title of the task
description (string, optional) - Detailed description of the task
due_date (string) - Due date in ISO format (YYYY-MM-DDTHH:MM:SS)
reminder_time (string, optional) - When to send reminder in ISO format
customer_number (string) - Customer's phone number in E.164 format (pattern: ^\+[1-9]\d{1,14}$)
6. getTasks
Get list of tasks for a user.
Parameters:
status (string, optional) - Filter by status (PENDING/IN_PROGRESS/COMPLETED/CANCELED)
customer_number (string) - Customer's phone number in E.164 format (pattern: ^\+[1-9]\d{1,14}$)
---
Note: All functions that require a phone number use the E.164 format pattern: ^\+[1-9]\d{1,14}$ (e.g., +1234567890)