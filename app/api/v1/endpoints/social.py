from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from app.db.session import get_db
from app.models.user import User
from app.models.social import Follow, Block
from app.api.deps import get_current_verified_user

router = APIRouter()


@router.post("/follow/{user_id}", response_model=dict)
async def follow_user(
    user_id: int,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Follow a user"""
    
    # Can't follow yourself
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot follow yourself"
        )
    
    # Check if user exists
    result = await db.execute(select(User).where(User.id == user_id))
    user_to_follow = result.scalar_one_or_none()
    
    if not user_to_follow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if already following
    result = await db.execute(
        select(Follow).where(
            and_(
                Follow.follower_id == current_user.id,
                Follow.followed_id == user_id
            )
        )
    )
    existing_follow = result.scalar_one_or_none()
    
    if existing_follow:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already following this user"
        )
    
    # Check if user is blocked
    result = await db.execute(
        select(Block).where(
            and_(
                Block.blocker_id == current_user.id,
                Block.blocked_id == user_id
            )
        )
    )
    is_blocked = result.scalar_one_or_none()
    
    if is_blocked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot follow a blocked user"
        )
    
    # Create follow relationship
    follow = Follow(
        follower_id=current_user.id,
        followed_id=user_id
    )
    db.add(follow)
    await db.commit()
    
    return {"message": "User followed successfully"}


@router.delete("/follow/{user_id}", response_model=dict)
async def unfollow_user(
    user_id: int,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Unfollow a user"""
    
    # Find follow relationship
    result = await db.execute(
        select(Follow).where(
            and_(
                Follow.follower_id == current_user.id,
                Follow.followed_id == user_id
            )
        )
    )
    follow = result.scalar_one_or_none()
    
    if not follow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not following this user"
        )
    
    await db.delete(follow)
    await db.commit()
    
    return {"message": "User unfollowed successfully"}


@router.post("/block/{user_id}", response_model=dict)
async def block_user(
    user_id: int,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Block a user"""
    
    # Can't block yourself
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot block yourself"
        )
    
    # Check if user exists
    result = await db.execute(select(User).where(User.id == user_id))
    user_to_block = result.scalar_one_or_none()
    
    if not user_to_block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if already blocked
    result = await db.execute(
        select(Block).where(
            and_(
                Block.blocker_id == current_user.id,
                Block.blocked_id == user_id
            )
        )
    )
    existing_block = result.scalar_one_or_none()
    
    if existing_block:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already blocked"
        )
    
    # Remove follow relationships if they exist
    await db.execute(
        select(Follow).where(
            or_(
                and_(
                    Follow.follower_id == current_user.id,
                    Follow.followed_id == user_id
                ),
                and_(
                    Follow.follower_id == user_id,
                    Follow.followed_id == current_user.id
                )
            )
        )
    )
    
    # Create block
    block = Block(
        blocker_id=current_user.id,
        blocked_id=user_id
    )
    db.add(block)
    await db.commit()
    
    return {"message": "User blocked successfully"}


@router.delete("/block/{user_id}", response_model=dict)
async def unblock_user(
    user_id: int,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Unblock a user"""
    
    # Find block relationship
    result = await db.execute(
        select(Block).where(
            and_(
                Block.blocker_id == current_user.id,
                Block.blocked_id == user_id
            )
        )
    )
    block = result.scalar_one_or_none()
    
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not blocked"
        )
    
    await db.delete(block)
    await db.commit()
    
    return {"message": "User unblocked successfully"}