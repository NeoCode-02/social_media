from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# Comment Create (for new top-level comments)
class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


# Reply Create (for replying to existing comments)
class ReplyCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


# Comment Update
class CommentUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


# Comment Response
class CommentResponse(BaseModel):
    id: int
    content: str
    photo_id: int
    author_id: int
    author_username: str
    author_profile_picture: Optional[str]
    parent_id: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]
    replies: List['CommentResponse'] = []
    
    class Config:
        from_attributes = True


# Needed for nested comments
CommentResponse.model_rebuild()
