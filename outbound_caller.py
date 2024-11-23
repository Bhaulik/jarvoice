import os
from loguru import logger
from dotenv import load_dotenv
import requests

# Load environment variables from .env.local
load_dotenv('.env.local')

# API Configuration
VAPI_BEARER_TOKEN = os.getenv("VAPI_BEARER_TOKEN")
VAPI_API_OUTBOUND_CALL_URL = os.getenv("VAPI_API_OUTBOUND_CALL_URL")

# Twilio Configuration
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

# Default Configuration
DEFAULT_VOICE_CONFIG = {
    "provider": "11labs",
    "voiceId": "sarah",
    "stability": 0.5,
    "similarityBoost": 0.5
}

DEFAULT_TRANSCRIBER_CONFIG = {
    "provider": "talkscriber",
    "language": "en",
    "model": "whisper"
}

DEFAULT_MODEL_CONFIG = {
    "provider": "openai",
    "model": "gpt-4-turbo-preview",
    "temperature": 0.8,
    "maxTokens": 150,
}

DEFAULT_TIMING_CONFIG = {
    "silenceTimeoutSeconds": 20,
    "maxDurationSeconds": 300,
    "startSpeakingPlan": {
        "waitSeconds": 0.3,
        "smartEndpointingEnabled": True,
        "transcriptionEndpointingPlan": {
            "onPunctuationSeconds": 0.2,
            "onNoPunctuationSeconds": 1.0,
            "onNumberSeconds": 0.5
        }
    },
    "stopSpeakingPlan": {
        "numWords": 3,
        "voiceSeconds": 0.3,
        "backoffSeconds": 0.8
    }
}

DEFAULT_VOICEMAIL_CONFIG = {
    "provider": "twilio",
    "enabled": True,
    "voicemailDetectionTypes": [
        "machine_end_beep",
        "machine_end_silence"
    ]
}

class OutboundCaller:
    def __init__(self):
        self.api_token = VAPI_BEARER_TOKEN
        self.api_url = VAPI_API_OUTBOUND_CALL_URL
        self.from_number = TWILIO_PHONE_NUMBER
        
        # Default configuration parameters
        self.default_config = {
            "voice": DEFAULT_VOICE_CONFIG,
            "transcriber": DEFAULT_TRANSCRIBER_CONFIG,
            "model": DEFAULT_MODEL_CONFIG,
            "timing": DEFAULT_TIMING_CONFIG,
            "voicemail": DEFAULT_VOICEMAIL_CONFIG
        }
    
    def _create_call_config(self, 
                           to_number: str,
                           name: str,
                           first_message: str,
                           system_prompt: str,
                           voicemail_message: str = None,
                           end_call_message: str = "Thank you for your time. Have a great day!",
                           end_call_phrases: list = None,
                           background_sound: str = "office",
                           **kwargs) -> dict:
        """
        Create a standardized call configuration with customizable parameters
        """
        if end_call_phrases is None:
            end_call_phrases = [
                "Thanks for your time. Goodbye!",
                "Have a wonderful day!",
                "Thank you, goodbye!"
            ]
            
        if voicemail_message is None:
            voicemail_message = f"{first_message} Please call us back at {self.from_number} at your convenience."

        return {
            "name": name,
            "type": "outboundPhoneCall",
            "assistant": {
                "name": kwargs.get("assistant_name", "Assistant"),
                "firstMessage": first_message,
                "firstMessageMode": "assistant-speaks-first",
                "transcriber": kwargs.get("transcriber", self.default_config["transcriber"]),
                "model": {
                    **self.default_config["model"],
                    "messages": [{
                        "role": "system",
                        "content": system_prompt
                    }],
                    "emotionRecognitionEnabled": kwargs.get("emotion_recognition", True)
                },
                "voice": kwargs.get("voice", self.default_config["voice"]),
                **self.default_config["timing"],
                "backgroundSound": background_sound,
                "voicemailDetection": kwargs.get("voicemail", self.default_config["voicemail"]),
                "voicemailMessage": voicemail_message,
                "endCallMessage": end_call_message,
                "endCallPhrases": end_call_phrases
            },
            "phoneNumber": {
                "twilioPhoneNumber": self.from_number,
                "twilioAccountSid": TWILIO_ACCOUNT_SID,
                "twilioAuthToken": TWILIO_AUTH_TOKEN
            },
            "customer": {
                "number": to_number
            }
        }

    def make_simple_call(self, to_number: str, message: str, **kwargs) -> str:
        """
        Make a simple outbound call with a custom message
        """
        logger.info(f"Initiating simple call to {to_number}")
        try:
            call_config = self._create_call_config(
                to_number=to_number,
                name="Simple Outbound Call",
                first_message=message,
                system_prompt="You are a professional assistant with a warm, caring personality. Speak naturally with brief pauses. Always acknowledge the person's responses and be helpful and courteous.",
                **kwargs
            )
            
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(self.api_url, json=call_config, headers=headers)
            response.raise_for_status()  # Raises an HTTPError for bad responses
            
            data = response.json()
            call_id = data.get('id', 'unknown')
            logger.info(f"Call successfully initiated - ID: {call_id}")
            return f"Call initiated - ID: {call_id}"
            
        except Exception as e:
            logger.error(f"Failed to make call to {to_number}: {str(e)}", exc_info=True)
            return f"Failed to make call: {str(e)}"

    def make_appointment_call(self, to_number: str, office_name: str = "Dr. Johnson's office", **kwargs) -> str:
        """
        Make an appointment scheduling call with comprehensive configuration
        """
        first_message = f"Hello! My name is Sarah calling from {office_name}. I'm following up about scheduling your appointment. Is this a convenient time to talk?"
        voicemail_message = f"Hi, this is Sarah from {office_name} calling about scheduling your appointment. Please call us back at your convenience at {self.from_number}. Have a great day!"
        
        try:
            call_config = self._create_call_config(
                to_number=to_number,
                name="Professional Appointment Booking Call",
                first_message=first_message,
                system_prompt="You are Sarah, a professional medical office scheduler. You have a warm, caring personality and speak naturally with brief pauses. Always acknowledge the person's responses. If they're busy, offer to call back later. Key tasks: 1) Confirm they're the right person 2) Briefly explain you're calling about their appointment 3) Work with their schedule to find a suitable time 4) Verify their information. Use conversational language like 'Great, let me check that for you' or 'I understand, would afternoon work better for you?'",
                voicemail_message=voicemail_message,
                end_call_message="Perfect, I've got your appointment scheduled. You'll receive a confirmation shortly. Thank you for your time, and have a great rest of your day!",
                end_call_phrases=[
                    "I'll send that confirmation right over. Have a great day!",
                    "You're all set for your appointment. Have a wonderful day!",
                    "Thank you for your time today, goodbye!"
                ],
                assistant_name="Appointment Scheduler",
                **kwargs
            )
            
            response = self.vapi_client.create_call(call_config)
            return f"Appointment call initiated - ID: {response.get('id', 'unknown')}"
            
        except Exception as e:
            logger.error(f"Appointment call failed: {str(e)}")
            return f"Failed to make appointment call: {str(e)}"

# # Example usage:
# caller = OutboundCaller()

# # Make a simple call
# result = caller.make_simple_call(
#     "+12045906645", 
#     "Hello! This is a test message."
# )
# print(result)

# # Make an appointment call
# result = caller.make_appointment_call(
#     "+12045906645", 
#     "City Dental Clinic"
# )
# print(result)

# # Sales Follow-up Call
# sales_call = caller.make_simple_call(
#     to_number="+1234567890",
#     message="Hi, this is Sarah from TechCorp following up about your recent interest in our cloud solutions. Do you have a moment to chat?",
#     system_prompt=(
#         "You are a professional sales representative who is warm yet direct. Key objectives:\n"
#         "1. Qualify the lead's current needs and timeline\n"
#         "2. Address any initial concerns empathetically\n"
#         "3. Focus on value proposition, not features\n"
#         "4. Guide towards a demo booking if interested\n\n"
#         "Use consultative selling techniques and avoid being pushy. Listen actively and mirror the customer's communication style.\n"
#         "If they're not interested, gracefully end the call while leaving the door open for future contact."
#     ),
#     assistant_name="Sales Consultant",
#     voice={
#         "provider": "11labs",
#         "voiceId": "sarah",
#         "stability": 0.7,
#         "similarityBoost": 0.7
#     },
#     background_sound="office_busy"
# )

# # Customer Support Follow-up
# support_call = caller.make_simple_call(
#     to_number="+1234567890",
#     message="Hello, I'm calling from TechCorp's customer success team regarding your recent support ticket. Is now a good time to discuss the resolution?",
#     system_prompt=(
#         "You are a technical support specialist with deep product knowledge. Your goals:\n"
#         "1. Verify the customer's satisfaction with the previous solution\n"
#         "2. Gather specific feedback about their experience\n"
#         "3. Offer additional assistance if needed\n"
#         "4. Document any new issues that arise\n\n"
#         "Show technical competence while remaining approachable. Use clear, non-technical language unless the customer demonstrates technical proficiency.\n"
#         "End the call with a clear next step if any issues remain unresolved."
#     ),
#     assistant_name="Support Specialist",
#     timing={
#         "silenceTimeoutSeconds": 30,
#         "maxDurationSeconds": 600  # Longer call time for technical discussions
#     }
# )

# # Event Registration Confirmation
# event_call = caller.make_simple_call(
#     to_number="+1234567890",
#     message="Hi, this is Alex from TechCorp's events team calling about your registration for next week's AI Summit.",
#     system_prompt=(
#         "You are an event coordinator responsible for confirming attendance and providing event details. Your tasks:\n"
#         "1. Confirm the attendee's participation\n"
#         "2. Share key logistical details (timing, location, parking)\n"
#         "3. Mention any special requirements (dress code, items to bring)\n"
#         "4. Answer questions about the agenda\n\n"
#         "Be enthusiastic but professional. If they can't attend, collect feedback and offer alternative dates or virtual options.\n"
#         "End with clear next steps and contact information for day-of support."
#     ),
#     assistant_name="Event Coordinator",
#     end_call_phrases=[
#         "Looking forward to seeing you at the summit!",
#         "We'll see you next week at the event!",
#         "Thank you for confirming, see you there!"
#     ],
#     background_sound="lobby"
# )

# # Survey/Research Call
# research_call = caller.make_simple_call(
#     to_number="+1234567890",
#     message="Hello, I'm conducting a brief 5-minute survey about recent experiences with remote work technology. Would you be willing to share your thoughts?",
#     system_prompt=(
#         "You are a market research interviewer collecting qualitative data. Guidelines:\n"
#         "1. Start with screening questions to ensure participant qualification\n"
#         "2. Use open-ended questions to gather detailed responses\n"
#         "3. Probe deeper with follow-up questions when receiving vague answers\n"
#         "4. Maintain neutrality - avoid leading questions or showing bias\n"
#         "5. Keep responses on track without being abrupt\n\n"
#         "If participant expresses time constraints, offer to schedule for later.\n"
#         "Thank participant and explain how their feedback will be used."
#     ),
#     assistant_name="Research Interviewer",
#     model={
#         "provider": "openai",
#         "model": "gpt-4-turbo-preview",
#         "temperature": 0.4,  # Lower temperature for more focused responses
#         "maxTokens": 200,
#         "emotionRecognitionEnabled": True
#     },
#     timing={
#         "silenceTimeoutSeconds": 25,
#         "maxDurationSeconds": 400
#     }
# )

# # Medical Test Results Follow-up
# medical_call = caller.make_simple_call(
#     to_number="+1234567890",
#     message="Hello, this is Sarah calling from Dr. Smith's office regarding your recent lab results. Is this a good time to talk?",
#     system_prompt=(
#         "You are a medical office assistant communicating routine test results. Important guidelines:\n"
#         "1. Verify patient identity before discussing any information\n"
#         "2. Use HIPAA-compliant language and maintain privacy\n"
#         "3. Explain results in clear, non-technical terms\n"
#         "4. Schedule follow-up appointments if needed\n"
#         "5. Document all communication attempts\n\n"
#         "If reaching voicemail, leave only a generic callback message without mentioning test results.\n"
#         "Handle patient concerns with empathy while staying within scope of authority."
#     ),
#     assistant_name="Medical Assistant",
#     voicemail={
#         "provider": "twilio",
#         "enabled": True,
#         "voicemailDetectionTypes": ["machine_end_beep", "machine_end_silence"],
#         "maxDuration": 30
#     },
#     background_sound="medical_office"
# )
