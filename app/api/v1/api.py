from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, photos, comments, chat, social

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(photos.router, prefix="/photos", tags=["Photos"])

# Comments: nested under photos for create/list, separate for update/delete/reply
api_router.include_router(
    comments.photo_comments_router, 
    prefix="/photos/{photo_id}/comments", 
    tags=["Comments"]
)
api_router.include_router(comments.router, prefix="/comments", tags=["Comments"])

api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(social.router, prefix="/social", tags=["Social"])
