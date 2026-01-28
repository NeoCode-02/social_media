from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# Category
class CategoryResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str]
    
    class Config:
        from_attributes = True


# Photo Create
class PhotoCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    category_ids: List[int] = Field(default_factory=list)


# Photo Update
class PhotoUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    category_ids: Optional[List[int]] = None


# Photo Response
class PhotoResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    file_path: str
    file_name: str
    width: Optional[int]
    height: Optional[int]
    owner_id: int
    owner_username: str
    views_count: int
    likes_count: int
    comments_count: int
    created_at: datetime
    updated_at: Optional[datetime]
    categories: List[CategoryResponse]
    is_liked: bool = False
    
    class Config:
        from_attributes = True


# Photo List Item (lighter version for lists)
class PhotoListItem(BaseModel):
    id: int
    title: str
    file_path: str
    width: Optional[int]
    height: Optional[int]
    owner_id: int
    owner_username: str
    likes_count: int
    comments_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# Photo Filter
class PhotoFilter(BaseModel):
    category_ids: Optional[List[int]] = None
    owner_id: Optional[int] = None
    search: Optional[str] = None
    skip: int = Field(0, ge=0)
    limit: int = Field(20, ge=1, le=100)