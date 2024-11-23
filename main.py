from fastapi import FastAPI
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

# Health check endpoint
@app.get("/events")
async def health_check():
    return {
        "event": "jarvoice-api",
        "service": "jarvoice-api"
    }

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


if __name__ == "__main__":
    api_token = os.getenv("VAPI_TOKEN")
    if not api_token:
        logger.error("VAPI_TOKEN environment variable not set")
        sys.exit(1)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)