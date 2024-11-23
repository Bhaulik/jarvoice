from tool_registry import ToolFunctionRegistry
from loguru import logger
from datetime import datetime, time
import uuid
import asyncio
from enum import Enum
from pydantic import BaseModel, Field
from loguru import logger

@ToolFunctionRegistry.register(
    name="sendMenuSMS",
    description="Send menu via SMS",
    arguments={
        "customer_number": {
            "type": "string",
            "description": "Customer's phone number in E.164 format",
            "required": False,
            "pattern": "^\+[1-9]\d{1,14}$"
        }
    }
)
def send_menu_sms(customer_number: str = None) -> str:
    """Send menu via SMS"""
    logger.info(f"Sending menu via SMS", customer_number=customer_number)
    return f"Menu sent via SMS to {customer_number}"

@ToolFunctionRegistry.register(
    name="testFunction",
    description="Test if the system is working properly",
    arguments={
        "customer_number": {
            "type": "string",
            "description": "Customer's phone number in E.164 format",
            "required": False,
            "pattern": "^\+[1-9]\d{1,14}$"
        }
    }
)
def test_function(customer_number: str = None) -> str:
    """Test system functionality"""
    print(f"This is a test function and the customer number is {customer_number}")
    return "Test successful for bhaulik"

@ToolFunctionRegistry.register(
    name="abcfunction",
    description="Adds two numbers together",
    arguments={
        "a": {
            "type": "number",
            "description": "First number to add",
            "required": True
        },
        "b": {
            "type": "number",
            "description": "Second number to add",
            "required": True
        },
                "customer_number": {
            "type": "string",
            "description": "Customer's phone number in E.164 format",
            "required": False,
            "pattern": "^\+[1-9]\d{1,14}$"
        }
    }
)
def abcfunction(a, b, customer_number) -> str:
    """Add two numbers together"""
    logger.info(f"Adding numbers", a=a, b=b)
    return "100 is the result"
