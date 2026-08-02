from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SessionMetadata(BaseModel):
    # Mongo's entire view of a session - never the secret content, never
    # the decryption key (the key lives only in the URL fragment, which
    # never reaches the backend at all). Just enough for basic abuse
    # tracking and observability: who created what, when, and whether it
    # was ever actually read.
    session_id: str
    created_at: datetime
    expires_at: datetime
    read: bool = False
    read_count: int = 0
    hashed_ip: Optional[str] = None
