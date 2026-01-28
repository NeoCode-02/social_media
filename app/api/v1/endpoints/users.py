from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import List

from app.db.session import get_db
from app.models.user import User
from app.models.social import Follow, Block
from app.models.photo import Photo
from app.schemas.user import UserResponse, UserUpdate, UserProfile, UserWithStats
from app.api.deps import get_current_user, get_current_verified_user
from app.utils.image import save_upload_file, delete_file
from app.core.config import settings

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """Get current user profile"""
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_profile(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user profile"""
    
    # Check if username is taken
    if user_data.username and user_data.username != current_user.username:
        result = await db.execute(
            select(User).where(
                and_(
                    User.username == user_data.username,
                    User.id != current_user.id
                )
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        current_user.username = user_data.username
    
    if user_data.bio is not None:
        current_user.bio = user_data.bio
    
    await db.commit()
    await db.refresh(current_user)
    
    return UserResponse.model_validate(current_user)


@router.post("/me/profile-picture", response_model=UserResponse)
async def upload_profile_picture(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload or update profile picture"""
    
    # Delete old profile picture if exists
    if current_user.profile_picture:
        delete_file(current_user.profile_picture)
    
    # Save new profile picture
    filepath, _, _, _ = await save_upload_file(
        file,
        upload_dir=settings.PROFILE_UPLOAD_DIR,
        compress=True
    )
    
    current_user.profile_picture = filepath
    await db.commit()
    await db.refresh(current_user)
    
    return UserResponse.model_validate(current_user)


@router.get("/{user_id}", response_model=UserWithStats)
async def get_user_profile(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user profile by ID"""
    
    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get stats
    followers_count = await db.scalar(
        select(func.count()).select_from(Follow).where(Follow.followed_id == user_id)
    )
    following_count = await db.scalar(
        select(func.count()).select_from(Follow).where(Follow.follower_id == user_id)
    )
    photos_count = await db.scalar(
        select(func.count()).select_from(Photo).where(Photo.owner_id == user_id)
    )
    
    # Check if current user is following this user
    is_following = False
    if current_user:
        result = await db.execute(
            select(Follow).where(
                and_(
                    Follow.follower_id == current_user.id,
                    Follow.followed_id == user_id
                )
            )
        )
        is_following = result.scalar_one_or_none() is not None
    
    # Check if current user has blocked this user
    is_blocked = False
    if current_user:
        result = await db.execute(
            select(Block).where(
                and_(
                    Block.blocker_id == current_user.id,
                    Block.blocked_id == user_id
                )
            )
        )
        is_blocked = result.scalar_one_or_none() is not None
    
    return UserWithStats(
        id=user.id,
        username=user.username,
        bio=user.bio,
        profile_picture=user.profile_picture,
        created_at=user.created_at,
        followers_count=followers_count or 0,
        following_count=following_count or 0,
        photos_count=photos_count or 0,
        is_following=is_following,
        is_blocked=is_blocked
    )


@router.get("/{user_id}/followers", response_model=List[UserProfile])
async def get_followers(
    user_id: int,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """Get user's followers"""
    
    result = await db.execute(
        select(User)
        .join(Follow, Follow.follower_id == User.id)
        .where(Follow.followed_id == user_id)
        .offset(skip)
        .limit(limit)
    )
    followers = result.scalars().all()
    
    return [UserProfile.model_validate(user) for user in followers]


@router.get("/{user_id}/following", response_model=List[UserProfile])
async def get_following(
    user_id: int,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """Get users that this user is following"""
    
    result = await db.execute(
        select(User)
        .join(Follow, Follow.followed_id == User.id)
        .where(Follow.follower_id == user_id)
        .offset(skip)
        .limit(limit)
    )
    following = result.scalars().all()
    
    return [UserProfile.model_validate(user) for user in following]