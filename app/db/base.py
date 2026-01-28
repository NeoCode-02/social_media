from app.db.session import Base
from app.models.user import User, EmailVerification, PasswordReset
from app.models.photo import Photo, PhotoCategory, PhotoLike, Category
from app.models.comment import Comment
from app.models.chat import ChatMessage
from app.models.social import Follow, Block

# Import all models here so Alembic can detect them
__all__ = [
    "Base",
    "User",
    "EmailVerification",
    "PasswordReset",
    "Photo",
    "PhotoCategory",
    "PhotoLike",
    "Category",
    "Comment",
    "ChatMessage",
    "Follow",
    "Block",
]