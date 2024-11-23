import requests
from datetime import datetime
from typing import Dict, Any, List
import os

class CalService:
    def __init__(self):
        self.api_url = os.environ.get("CAL_API_URL")
        self.headers = {
            "Authorization": f"Bearer {os.environ.get('CAL_API_KEY')}",
            "Content-Type": "application/json"
        }
    
    async def sync_event_to_cal(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Sync an event to Cal.com"""
        endpoint = f"{self.api_url}/organizations/{event['org_id']}/teams/{event['team_id']}/event-types"
        
        cal_event = {
            "title": event["title"],
            "description": event["description"],
            "lengthInMinutes": event.get("duration", 60),
            "slug": event.get("slug", event["title"].lower().replace(" ", "-")),
            "locations": event.get("locations", []),
            "bookingFields": event.get("booking_fields", []),
            "disableGuests": event.get("disable_guests", False),
            "minimumBookingNotice": event.get("min_booking_notice", 0),
            "beforeEventBuffer": event.get("before_buffer", 0),
            "afterEventBuffer": event.get("after_buffer", 0),
            "seats": event.get("seats", None),
            "hosts": event.get("hosts", []),
            "schedulingType": event.get("scheduling_type", {}),
            "customName": event.get("custom_name", None),
        }
        
        # Remove None values to keep the payload clean
        cal_event = {k: v for k, v in cal_event.items() if v is not None}
        
        response = requests.post(endpoint, json=cal_event, headers=self.headers)
        if response.status_code not in (200, 201):
            raise Exception(f"Failed to sync with Cal.com: {response.text}")
            
        return response.json()
    
    async def get_cal_events(self) -> List[Dict[str, Any]]:
        """Fetch events from Cal.com"""
        endpoint = f"{self.api_url}/schedules"
        response = requests.get(endpoint, headers=self.headers)
        
        if response.status_code != 200:
            raise Exception(f"Failed to fetch Cal.com events: {response.text}")
            
        return response.json()
