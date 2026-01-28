from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime


# User Registration
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    
    @validator('username')
    def username_alphanumeric(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username must be alphanumeric (with _ or - allowed)')
        return v


# Email Verification
class EmailVerificationRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)


class ResendVerificationRequest(BaseModel):
    email: EmailStr


# Login
class UserLogin(BaseModel):
    email: EmailStr
    password: str


# Password Reset
class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


# User Profile Update
class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    bio: Optional[str] = Field(None, max_length=500)
    
    @validator('username')
    def username_alphanumeric(cls, v):
        if v and not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username must be alphanumeric (with _ or - allowed)')
        return v


# User Response
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    bio: Optional[str]
    profile_picture: Optional[str]
    is_verified: bool
    is_oauth: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# User Profile (public view)
class UserProfile(BaseModel):
    id: int
    username: str
    bio: Optional[str]
    profile_picture: Optional[str]
    created_at: datetime
    followers_count: int = 0
    following_count: int = 0
    photos_count: int = 0
    
    class Config:
        from_attributes = True


# User with additional info
class UserWithStats(UserProfile):
    is_following: bool = False
    is_blocked: bool = False
    
    class Config:
        from_attributes = True