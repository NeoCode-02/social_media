from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.db.session import get_db
from app.models.user import User
from app.models.photo import Photo
from app.models.comment import Comment
from app.schemas.comment import CommentCreate, CommentResponse, CommentUpdate, ReplyCreate
from app.api.deps import get_current_verified_user

# Router for /photos/{photo_id}/comments endpoints
photo_comments_router = APIRouter()

# Router for /comments/{comment_id} endpoints
router = APIRouter()


async def build_comment_tree(comments: List[Comment], db: AsyncSession) -> List[CommentResponse]:
    """Build nested comment structure"""
    comment_dict = {}
    root_comments = []
    
    # First pass: create all comment responses
    for comment in comments:
        author_result = await db.execute(select(User).where(User.id == comment.author_id))
        author = author_result.scalar_one()
        
        comment_response = CommentResponse(
            id=comment.id,
            content=comment.content,
            photo_id=comment.photo_id,
            author_id=comment.author_id,
            author_username=author.username,
            author_profile_picture=author.profile_picture,
            parent_id=comment.parent_id,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
            replies=[]
        )
        comment_dict[comment.id] = comment_response
        
        if comment.parent_id is None:
            root_comments.append(comment_response)
    
    # Second pass: build tree structure
    for comment in comments:
        if comment.parent_id is not None and comment.parent_id in comment_dict:
            parent = comment_dict[comment.parent_id]
            parent.replies.append(comment_dict[comment.id])
    
    return root_comments


# ============ Photo Comments Router (/photos/{photo_id}/comments) ============

@photo_comments_router.post("", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    photo_id: int,
    comment_data: CommentCreate,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a comment on a photo"""
    
    # Check if photo exists
    result = await db.execute(select(Photo).where(Photo.id == photo_id))
    photo = result.scalar_one_or_none()
    
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found"
        )
    
    # Create comment
    comment = Comment(
        content=comment_data.content,
        photo_id=photo_id,
        author_id=current_user.id,
        parent_id=None
    )
    db.add(comment)
    
    # Increment comments count on photo
    photo.comments_count += 1
    
    await db.commit()
    await db.refresh(comment)
    
    return CommentResponse(
        id=comment.id,
        content=comment.content,
        photo_id=comment.photo_id,
        author_id=comment.author_id,
        author_username=current_user.username,
        author_profile_picture=current_user.profile_picture,
        parent_id=comment.parent_id,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        replies=[]
    )


@photo_comments_router.get("", response_model=List[CommentResponse])
async def get_comments(
    photo_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get all comments for a photo (nested structure)"""
    
    # Check if photo exists
    result = await db.execute(select(Photo).where(Photo.id == photo_id))
    photo = result.scalar_one_or_none()
    
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found"
        )
    
    # Get all comments for this photo
    result = await db.execute(
        select(Comment)
        .where(Comment.photo_id == photo_id)
        .order_by(Comment.created_at.asc())
    )
    comments = result.scalars().all()
    
    # Build nested structure
    return await build_comment_tree(comments, db)


# ============ Comments Router (/comments/{comment_id}) ============

@router.post("/{comment_id}/reply", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def reply_to_comment(
    comment_id: int,
    reply_data: ReplyCreate,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Reply to an existing comment"""
    
    # Get parent comment
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    parent_comment = result.scalar_one_or_none()
    
    if not parent_comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent comment not found"
        )
    
    # Get photo to increment comment count
    result = await db.execute(select(Photo).where(Photo.id == parent_comment.photo_id))
    photo = result.scalar_one_or_none()
    
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found"
        )
    
    # Create reply
    reply = Comment(
        content=reply_data.content,
        photo_id=parent_comment.photo_id,
        author_id=current_user.id,
        parent_id=comment_id
    )
    db.add(reply)
    
    # Increment comments count
    photo.comments_count += 1
    
    await db.commit()
    await db.refresh(reply)
    
    return CommentResponse(
        id=reply.id,
        content=reply.content,
        photo_id=reply.photo_id,
        author_id=reply.author_id,
        author_username=current_user.username,
        author_profile_picture=current_user.profile_picture,
        parent_id=reply.parent_id,
        created_at=reply.created_at,
        updated_at=reply.updated_at,
        replies=[]
    )


@router.put("/{comment_id}", response_model=CommentResponse)
async def update_comment(
    comment_id: int,
    comment_data: CommentUpdate,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a comment (author only)"""
    
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    
    if comment.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this comment"
        )
    
    comment.content = comment_data.content
    await db.commit()
    await db.refresh(comment)
    
    return CommentResponse(
        id=comment.id,
        content=comment.content,
        photo_id=comment.photo_id,
        author_id=comment.author_id,
        author_username=current_user.username,
        author_profile_picture=current_user.profile_picture,
        parent_id=comment.parent_id,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        replies=[]
    )


@router.delete("/{comment_id}", response_model=dict)
async def delete_comment(
    comment_id: int,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a comment (author only)"""
    
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    
    if comment.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this comment"
        )
    
    # Get photo to decrement comment count
    result = await db.execute(select(Photo).where(Photo.id == comment.photo_id))
    photo = result.scalar_one_or_none()
    
    if photo:
        photo.comments_count = max(0, photo.comments_count - 1)
    
    # Delete comment (cascade will delete replies)
    await db.delete(comment)
    await db.commit()
    
    return {"message": "Comment deleted successfully"}
