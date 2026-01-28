from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Table
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base


# Association table for photo categories (many-to-many)
class PhotoCategory(Base):
    __tablename__ = "photo_categories"
    
    photo_id = Column(Integer, ForeignKey("photos.id", ondelete="CASCADE"), primary_key=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True)


class Category(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    slug = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    photos = relationship(
        "Photo",
        secondary="photo_categories",
        back_populates="categories"
    )
    
    def __repr__(self):
        return f"<Category {self.name}>"


class Photo(Base):
    __tablename__ = "photos"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    file_path = Column(String(500), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)  # in bytes
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    views_count = Column(Integer, default=0)
    likes_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    owner = relationship("User", back_populates="photos")
    categories = relationship(
        "Category",
        secondary="photo_categories",
        back_populates="photos"
    )
    likes = relationship("PhotoLike", back_populates="photo", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="photo", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Photo {self.title}>"


class PhotoLike(Base):
    __tablename__ = "photo_likes"
    
    id = Column(Integer, primary_key=True, index=True)
    photo_id = Column(Integer, ForeignKey("photos.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    photo = relationship("Photo", back_populates="likes")
    user = relationship("User", back_populates="likes")
    
    # Ensure a user can only like a photo once
    __table_args__ = (
        {"schema": None, "extend_existing": True},
    )
    
    def __repr__(self):
        return f"<PhotoLike photo_id={self.photo_id} user_id={self.user_id}>"