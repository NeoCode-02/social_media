from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base


class Follow(Base):
    __tablename__ = "follows"
    
    id = Column(Integer, primary_key=True, index=True)
    follower_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    followed_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    follower = relationship("User", foreign_keys=[follower_id], back_populates="following")
    followed = relationship("User", foreign_keys=[followed_id], back_populates="followers")
    
    # Ensure a user can only follow another user once
    __table_args__ = (
        UniqueConstraint('follower_id', 'followed_id', name='unique_follow'),
    )
    
    def __repr__(self):
        return f"<Follow follower_id={self.follower_id} followed_id={self.followed_id}>"


class Block(Base):
    __tablename__ = "blocks"
    
    id = Column(Integer, primary_key=True, index=True)
    blocker_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    blocked_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    blocker = relationship("User", foreign_keys=[blocker_id], back_populates="blocking")
    blocked = relationship("User", foreign_keys=[blocked_id], back_populates="blocked_by")
    
    # Ensure a user can only block another user once
    __table_args__ = (
        UniqueConstraint('blocker_id', 'blocked_id', name='unique_block'),
    )
    
    def __repr__(self):
        return f"<Block blocker_id={self.blocker_id} blocked_id={self.blocked_id}>"