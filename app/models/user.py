from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)  # Nullable for OAuth users
    bio = Column(Text, nullable=True)
    profile_picture = Column(String(500), nullable=True)
    
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_oauth = Column(Boolean, default=False)
    oauth_provider = Column(String(50), nullable=True)  # 'google', etc.
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    photos = relationship("Photo", back_populates="owner", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="author", cascade="all, delete-orphan")
    likes = relationship("PhotoLike", back_populates="user", cascade="all, delete-orphan")
    
    # Following relationships
    following = relationship(
        "Follow",
        foreign_keys="Follow.follower_id",
        back_populates="follower",
        cascade="all, delete-orphan"
    )
    followers = relationship(
        "Follow",
        foreign_keys="Follow.followed_id",
        back_populates="followed",
        cascade="all, delete-orphan"
    )
    
    # Blocking relationships
    blocking = relationship(
        "Block",
        foreign_keys="Block.blocker_id",
        back_populates="blocker",
        cascade="all, delete-orphan"
    )
    blocked_by = relationship(
        "Block",
        foreign_keys="Block.blocked_id",
        back_populates="blocked",
        cascade="all, delete-orphan"
    )
    
    # Chat messages
    sent_messages = relationship(
        "ChatMessage",
        foreign_keys="ChatMessage.sender_id",
        back_populates="sender",
        cascade="all, delete-orphan"
    )
    received_messages = relationship(
        "ChatMessage",
        foreign_keys="ChatMessage.receiver_id",
        back_populates="receiver",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<User {self.username}>"


class EmailVerification(Base):
    __tablename__ = "email_verifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    email = Column(String(255), nullable=False)
    code = Column(String(6), nullable=False)
    is_used = Column(Boolean, default=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<EmailVerification {self.email}>"


class PasswordReset(Base):
    __tablename__ = "password_resets"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    email = Column(String(255), nullable=False)
    token = Column(String(255), nullable=False, unique=True, index=True)
    is_used = Column(Boolean, default=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<PasswordReset {self.email}>"