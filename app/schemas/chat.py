from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# Message Send
class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


# Message Response
class MessageResponse(BaseModel):
    id: int
    content: str
    sender_id: int
    receiver_id: int
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# Conversation Summary
class ConversationResponse(BaseModel):
    user_id: int
    username: str
    profile_picture: Optional[str]
    last_message: Optional[str]
    last_message_time: Optional[datetime]
    unread_count: int
    
    class Config:
        from_attributes = True


# WebSocket Message Types
class WSMessage(BaseModel):
    type: str  # "message", "typing", "read"
    content: Optional[str] = None
    receiver_id: Optional[int] = None
    message_id: Optional[int] = None


# Message History Request
class MessageHistoryRequest(BaseModel):
    skip: int = Field(0, ge=0)
    limit: int = Field(50, ge=1, le=100)