import httpx
import asyncio
import uuid
from datetime import datetime
from logger import logger

GA_MEASUREMENT_ID = "G-9S6CF8ERY0"
GA_API_SECRET = None

class GoogleAnalytics:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=5.0)
        self.measurement_id = GA_MEASUREMENT_ID
        self.api_secret = GA_API_SECRET

    async def track_event(self, event_name: str, params: dict, client_id: str = None):
        if not client_id:
            client_id = str(uuid.uuid4())

        payload = {
            "client_id": client_id,
            "events": [{
                "name": event_name,
                "params": {
                    **params,
                    "engagement_time_msec": "100"
                }
            }]
        }

        url = f"https://www.google-analytics.com/mp/collect?measurement_id={self.measurement_id}"
        if self.api_secret:
            url += f"&api_secret={self.api_secret}"

        try:
            response = await self.client.post(url, json=payload)
            if response.status_code == 204:
                logger.debug(f"GA4 event tracked: {event_name}")
            else:
                logger.warning(f"GA4 tracking failed: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"GA4 tracking error: {str(e)}")

    async def close(self):
        await self.client.aclose()

analytics = GoogleAnalytics()
