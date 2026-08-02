from datetime import datetime

from pydantic import BaseModel, Field


class SessionCreateResponse(BaseModel):
    session_id: str
    expires_at: datetime


class SecretSubmission(BaseModel):
    # Stage 1: this is plaintext, submitted straight from the sender's
    # browser. From Stage 3 on, the frontend encrypts client-side first,
    # so this field holds ciphertext instead - the backend's job doesn't
    # change either way: store opaque bytes, never inspect or log them.
    #
    # max_length caps how much someone can shove into a single session so
    # this can't be used as free unbounded blob storage.
    content: str = Field(..., min_length=1, max_length=64_000)


class SecretReadResponse(BaseModel):
    content: str
