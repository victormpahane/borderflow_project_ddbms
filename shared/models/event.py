from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Any


class Event(BaseModel):
    event_id: str
    container_id: str
    site_id: str
    event_type: str
    timestamp: datetime
    payload: Dict[str, Any]
    sync_status: str  # PENDING | SENT | RECEIVED
    sequence_number: int | None = None


class CreateEventRequest(BaseModel):
    container_id: str
    event_type: str
    payload: Dict[str, Any] = {}
