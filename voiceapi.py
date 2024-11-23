from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field, create_model
from typing import List, Dict, Any, Callable, TypeVar, Optional, Union, Type
from functools import wraps
from loguru import logger
import traceback
import json
import inspect
from enum import Enum
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from contextlib import asynccontextmanager
from registry import ToolFunctionRegistry, console
from business import BUSINESS
from utils.sms import send_sms



app = FastAPI(lifespan=lifespan)
console = Console()

# FastAPI Endpoints
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
                    logger.info(f"Function '{function_name}' executed successfully")
                except ValueError as ve:
                    result_text = str(ve)
                    logger.warning(result_text)
                except Exception as e:
                    result_text = f"Error executing function '{function_name}': {str(e)}"
                    logger.error(result_text)
                
                results.append({
                    "toolCallId": call_id,
                    "result": result_text
                })
            
            logger.info(f"Returning results: {results}")
            return {"results": results}
        
        logger.info("No tool calls found in any location")
        return {"results": []}

    except Exception as e:
        logger.error(f"Error in webhook: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="An error occurred while processing the request.")

@app.get("/functions/{function_name}")
async def get_function_spec(function_name: str):
    """Get specification for a specific function"""
    if function_name not in ToolFunctionRegistry._registry:
        raise HTTPException(status_code=404, detail=f"Function '{function_name}' not found")
    return ToolFunctionRegistry._registry[function_name]["metadata"]

@app.get("/functions")
async def list_functions():
    """List all registered functions and their specifications"""
    return {
        name: info["metadata"] 
        for name, info in ToolFunctionRegistry._registry.items()
    }

@ToolFunctionRegistry.register(
    name="transferToManager",
    description="Transfer call to manager",
    arguments={
        "managerphone": {
            "type": "string",
            "description": "Manager's phone number",
            "required": True
        },
        "reason": {
            "type": "string",
            "description": "Reason for transfer",
            "required": True
        },
        "customer_number": {
            "type": "string",
            "description": "Customer's phone number in E.164 format (e.g., +12045906645)",
            "required": False,
            "pattern": "^\+[1-9]\d{1,14}$"
        }
    }
)

def transfer_to_manager(managerphone: str, reason: str, customer_number: str = None) -> str:
    """Transfer call to manager"""
    return f"Call transferred to manager at {managerphone}. Reason: {reason}"

@ToolFunctionRegistry.register(
    name="sendMenuSMS",
    description="Send menu via SMS",
    arguments={
        "customer_number": {
            "type": "string",
            "description": "Customer's phone number in E.164 format (e.g., +12045906645)",
            "required": False,
            "pattern": "^\+[1-9]\d{1,14}$"
        }
    }
)
def send_menu_sms(customer_number: str = None) -> str:
    """Send menu via SMS"""
    if not customer_number:
        return "No phone number provided"
    
    try:
        menu_link = BUSINESS.links.get("menu_link")
        if not menu_link:
            return "Menu link not configured for this business"
            
        message = f"Here's our menu: {menu_link}"
        if send_sms(to_number=customer_number, message=message):
            return f"Menu SMS sent successfully to {customer_number}"
        else:
            return "Failed to send SMS"
    except Exception as e:
        logger.error(f"Failed to send SMS: {str(e)}")
        return f"Failed to send SMS: {str(e)}"
