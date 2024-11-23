from typing import Dict, Any, Callable
from rich.console import Console
from rich.table import Table
from loguru import logger
from typing import Dict, Any, Optional, ForwardRef, List, Callable
from functools import wraps
from pydantic import BaseModel, field_validator

console = Console()

from pydantic import BaseModel
from typing import Dict, Any, Optional
from enum import Enum

class ArgumentType(str, Enum):
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"

class ToolArgumentSpec(BaseModel):
    type: ArgumentType
    description: str
    required: bool = False
    items: Optional[Dict] = None  # Keep the full items structure
    properties: Optional[Dict] = None
    enum: Optional[List[str]] = None
    pattern: Optional[str] = None
    minimum: Optional[int] = None

    def dict(self, *args, **kwargs):
        d = super().dict(*args, **kwargs)
        # Remove None values
        return {k: v for k, v in d.items() if v is not None}

    model_config = {
        "arbitrary_types_allowed": True
    }

class ToolFunctionMetadata(BaseModel):
    name: str
    description: str
    arguments: Dict[str, ToolArgumentSpec]

    @field_validator('description')
    def validate_description(cls, v):
        if not isinstance(v, str):
            raise ValueError('Description must be a string')
        return v

class ToolCallFunction(BaseModel):
    name: str
    arguments: Dict[str, Any]
    _return_value: Optional[str] = None  # Private field to store return value

    def validate_return_value(self, value: Any) -> str:
        """Validate that the function return value is a string"""
        if not isinstance(value, str):
            raise ValueError(f'Tool function must return a string, got {type(value)}')
        self._return_value = value
        return value

    class Config:
        extra = "allow"

class ToolCall(BaseModel):
    id: str
    type: str
    function: ToolCallFunction

    class Config:
        extra = "allow" 
        
# Registry System
class ToolFunctionRegistry:
    """Enhanced registry for tool functions with strict validation and argument logging"""
    _registry: Dict[str, Dict[str, Any]] = {}
    
    @classmethod
    def show_registered_functions(cls):
        """Display all registered functions and their arguments in a formatted table"""
        table = Table(title="Registered Tool Functions")
        table.add_column("Function Name", style="cyan", no_wrap=True)
        table.add_column("Description", style="green")
        table.add_column("Arguments", style="yellow")

        for name, info in cls._registry.items():
            metadata = info["metadata"]
            # Create a bulleted list of arguments
            args_list = []
            for arg_name, arg_spec in metadata.arguments.items():
                requirement = "" if arg_spec.required else " (optional)"
                args_list.append(f"• {arg_name}: {arg_spec.type}{requirement}")
            
            # Join with newlines and add padding
            args_str = "\n".join(args_list) if args_list else "No arguments required"
            
            table.add_row(
                name,  # Function name
                metadata.description,  # Description
                args_str  # Arguments as bulleted list
            )
            table.add_row("----------------------------", "-------------------------------------------", "--------------------------------------------------------")  # Add separator row after each function's arguments

        console.print(table)

    @classmethod
    def print_function_args(cls, function_name: str):
        """Print arguments for a specific function"""
        if function_name not in cls._registry:
            console.print(f"[red]Function '{function_name}' not found![/red]")
            return

        metadata = cls._registry[function_name]["metadata"]
        table = Table(title=f"Arguments for {function_name}")
        table.add_column("Argument", style="cyan")
        table.add_column("Type", style="yellow")
        table.add_column("Required", style="green")
        table.add_column("Description", style="blue")

        for arg_name, arg_spec in metadata.arguments.items():
            table.add_row(
                arg_name,
                arg_spec.type.value,
                "✓" if arg_spec.required else "optional",
                arg_spec.description
            )

        console.print(table)

    @classmethod
    def register(cls, 
                name: str, 
                description: str,
                arguments: Dict[str, Dict[str, Any]]) -> Callable:
        """
        Enhanced decorator to register a tool function with strict validation and argument logging
        """
        # Convert raw argument specs to ToolArgumentSpec objects
        validated_args = {
            arg_name: ToolArgumentSpec(
                type=ArgumentType(arg_spec["type"]),
                description=arg_spec.get("description", ""),
                required=arg_spec.get("required", True),
                default=arg_spec.get("default", None)
            )
            for arg_name, arg_spec in arguments.items()
        }

        def decorator(func: Callable) -> Callable:
            # Log the registration with detailed argument information
            console.print(f"\n[cyan]Registering function:[/cyan] [bold]{name}[/bold]")
            console.print(f"[green]Description:[/green] {description}")
            console.print("[yellow]Arguments:[/yellow]")
            
            for arg_name, arg_spec in validated_args.items():
                req_status = "[green]required[/green]" if arg_spec.required else "[blue]optional[/blue]"
                console.print(f"  • [bold]{arg_name}[/bold] ({arg_spec.type}): {req_status}")
                console.print(f"    {arg_spec.description}")

            @wraps(func)
            def wrapper(**kwargs: Any) -> Any:
                try:
                    # Log incoming arguments during execution
                    logger.info(f"Executing {name} with arguments: {kwargs}")
                    return func(**kwargs)
                except Exception as e:
                    error_msg = str(e)
                    if "missing" in error_msg.lower():
                        # Show available arguments when missing args error occurs
                        logger.error(f"Missing arguments for {name}. Expected arguments:")
                        cls.print_function_args(name)
                    raise ValueError(f"Error executing {name}: {error_msg}")

            cls._registry[name] = {
                "function": wrapper,
                "metadata": ToolFunctionMetadata(
                    name=name,
                    description=description,
                    arguments=validated_args
                )
            }
            return wrapper
        return decorator

    @classmethod
    def execute(cls, name: str, args: Dict[str, Any]) -> str:
        """Execute a registered tool function with enhanced error handling and argument logging"""
        if name not in cls._registry:
            logger.error(f"Function '{name}' not found. Available functions:")
            cls.show_registered_functions()
            raise ValueError(f"Function '{name}' is not registered")
        
        try:
            logger.info(f"Executing {name} with arguments: {args}")
            func_info = cls._registry[name]
            return func_info["function"](**args)
        except Exception as e:
            logger.error(f"Error executing {name}: {str(e)}")
            cls.print_function_args(name)  # Show expected arguments on error
            raise
    
