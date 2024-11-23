from twilio.rest import Client
import os
from dotenv import load_dotenv
from typing import Optional

# Load environment variables
load_dotenv('.env.local')

def send_sms(to_number: str, message: str, from_number: Optional[str] = None, **kwargs) -> dict:
    """
    Send an SMS message using Twilio
    
    Args:
        to_number (str): The recipient's phone number
        message (str): The message content
        from_number (Optional[str]): The sender's phone number (defaults to env var)
        **kwargs: Additional keyword arguments (ignored)
    
    Returns:
        dict: Response from Twilio API
    """
    try:
        # Initialize Twilio client with credentials from .env
        client = Client(
            os.getenv('TWILIO_ACCOUNT_SID'),
            os.getenv('TWILIO_AUTH_TOKEN')
        )
        
        # Send message
        message = client.messages.create(
            body=message,
            from_=from_number or os.getenv('TWILIO_PHONE_NUMBER'),
            to=to_number
        )
        
        print(f"Message sent successfully! SID: {message.sid}")
        return {
            'sid': message.sid,
            'status': message.status,
            'error_message': message.error_message
        }
        
    except Exception as e:
        print(f"Error sending message: {str(e)}")
        return {
            'error': True,
            'message': str(e)
        }

# Example usage:
# send_sms("+1234567890", "Hello from your app!")
