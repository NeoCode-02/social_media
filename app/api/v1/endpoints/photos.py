from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from typing import List, Optional

from app.db.session import get_db
from app.models.user import User
from app.models.photo import Photo, PhotoLike, Category, PhotoCategory
from app.schemas.photo import PhotoResponse, PhotoCreate, PhotoUpdate, PhotoListItem, PhotoFilter, CategoryResponse
from app.api.deps import get_current_verified_user, get_optional_current_user
from app.utils.image import save_upload_file, delete_file, get_file_url

router = APIRouter()


@router.get("/categories", response_model=List[CategoryResponse])
async def get_categories(db: AsyncSession = Depends(get_db)):
    """Get all available categories"""
    result = await db.execute(select(Category).order_by(Category.name))
    categories = result.scalars().all()
    return [CategoryResponse.model_validate(cat) for cat in categories]


@router.post("", response_model=PhotoResponse, status_code=status.HTTP_201_CREATED)
async def upload_photo(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    category_ids: str = Form(""),  # Comma-separated category IDs
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload a new photo"""
    
    # Save photo file
    filepath, file_size, width, height = await save_upload_file(file, compress=True)
    
    # Create photo record
    photo = Photo(
        title=title,
        description=description,
        file_path=filepath,
        file_name=file.filename,
        file_size=file_size,
        width=width,
        height=height,
        owner_id=current_user.id
    )
    db.add(photo)
    await db.flush()
    
    # Add categories
    if category_ids:
        cat_id_list = [int(cid.strip()) for cid in category_ids.split(",") if cid.strip()]
        for cat_id in cat_id_list:
            photo_cat = PhotoCategory(photo_id=photo.id, category_id=cat_id)
            db.add(photo_cat)
    
    await db.commit()
    await db.refresh(photo)
    
    # Load categories
    result = await db.execute(
        select(Category)
        .join(PhotoCategory)
        .where(PhotoCategory.photo_id == photo.id)
    )
    categories = result.scalars().all()
    
    return PhotoResponse(
        id=photo.id,
        title=photo.title,
        description=photo.description,
        file_path=get_file_url(photo.file_path),
        file_name=photo.file_name,
        width=photo.width,
        height=photo.height,
        owner_id=photo.owner_id,
        owner_username=current_user.username,
        views_count=photo.views_count,
        likes_count=photo.likes_count,
        comments_count=photo.comments_count,
        created_at=photo.created_at,
        updated_at=photo.updated_at,
        categories=[CategoryResponse.model_validate(cat) for cat in categories],
        is_liked=False
    )


@router.get("", response_model=List[PhotoListItem])
async def list_photos(
    category_ids: Optional[str] = None,
    owner_id: Optional[int] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """List photos with filters (search, category, owner)"""
    
    query = select(Photo).join(User, Photo.owner_id == User.id)
    
    # Filter by categories
    if category_ids:
        cat_id_list = [int(cid.strip()) for cid in category_ids.split(",") if cid.strip()]
        query = query.join(PhotoCategory).where(PhotoCategory.category_id.in_(cat_id_list))
    
    # Filter by owner
    if owner_id:
        query = query.where(Photo.owner_id == owner_id)
    
    # Search in title and description
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Photo.title.ilike(search_term),
                Photo.description.ilike(search_term)
            )
        )
    
    # Order by created_at descending
    query = query.order_by(Photo.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    photos = result.scalars().all()
    
    # Build response
    photo_list = []
    for photo in photos:
        owner_result = await db.execute(select(User).where(User.id == photo.owner_id))
        owner = owner_result.scalar_one()
        
        photo_list.append(PhotoListItem(
            id=photo.id,
            title=photo.title,
            file_path=get_file_url(photo.file_path),
            width=photo.width,
            height=photo.height,
            owner_id=photo.owner_id,
            owner_username=owner.username,
            likes_count=photo.likes_count,
            comments_count=photo.comments_count,
            created_at=photo.created_at
        ))
    
    return photo_list


@router.get("/{photo_id}", response_model=PhotoResponse)
async def get_photo(
    photo_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """Get photo by ID"""
    
    result = await db.execute(select(Photo).where(Photo.id == photo_id))
    photo = result.scalar_one_or_none()
    
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found"
        )
    
    # Increment views
    photo.views_count += 1
    await db.commit()
    
    # Get owner
    owner_result = await db.execute(select(User).where(User.id == photo.owner_id))
    owner = owner_result.scalar_one()
    
    # Get categories
    cat_result = await db.execute(
        select(Category).join(PhotoCategory).where(PhotoCategory.photo_id == photo.id)
    )
    categories = cat_result.scalars().all()
    
    # Check if current user liked this photo
    is_liked = False
    if current_user:
        like_result = await db.execute(
            select(PhotoLike).where(
                and_(
                    PhotoLike.photo_id == photo_id,
                    PhotoLike.user_id == current_user.id
                )
            )
        )
        is_liked = like_result.scalar_one_or_none() is not None
    
    return PhotoResponse(
        id=photo.id,
        title=photo.title,
        description=photo.description,
        file_path=get_file_url(photo.file_path),
        file_name=photo.file_name,
        width=photo.width,
        height=photo.height,
        owner_id=photo.owner_id,
        owner_username=owner.username,
        views_count=photo.views_count,
        likes_count=photo.likes_count,
        comments_count=photo.comments_count,
        created_at=photo.created_at,
        updated_at=photo.updated_at,
        categories=[CategoryResponse.model_validate(cat) for cat in categories],
        is_liked=is_liked
    )


@router.delete("/{photo_id}", response_model=dict)
async def delete_photo(
    photo_id: int,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a photo (owner only)"""
    
    result = await db.execute(select(Photo).where(Photo.id == photo_id))
    photo = result.scalar_one_or_none()
    
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found"
        )
    
    if photo.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this photo"
        )
    
    # Delete file
    delete_file(photo.file_path)
    
    # Delete from database
    await db.delete(photo)
    await db.commit()
    
    return {"message": "Photo deleted successfully"}


@router.post("/{photo_id}/like", response_model=dict)
async def like_photo(
    photo_id: int,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Like a photo"""
    
    # Check if photo exists
    result = await db.execute(select(Photo).where(Photo.id == photo_id))
    photo = result.scalar_one_or_none()
    
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found"
        )
    
    # Check if already liked
    result = await db.execute(
        select(PhotoLike).where(
            and_(
                PhotoLike.photo_id == photo_id,
                PhotoLike.user_id == current_user.id
            )
        )
    )
    existing_like = result.scalar_one_or_none()
    
    if existing_like:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Photo already liked"
        )
    
    # Create like
    like = PhotoLike(photo_id=photo_id, user_id=current_user.id)
    db.add(like)
    
    # Increment likes count
    photo.likes_count += 1
    
    await db.commit()
    
    return {"message": "Photo liked successfully"}


@router.delete("/{photo_id}/like", response_model=dict)
async def unlike_photo(
    photo_id: int,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Unlike a photo"""
    
    # Find like
    result = await db.execute(
        select(PhotoLike).where(
            and_(
                PhotoLike.photo_id == photo_id,
                PhotoLike.user_id == current_user.id
            )
        )
    )
    like = result.scalar_one_or_none()
    
    if not like:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not liked"
        )
    
    # Get photo
    result = await db.execute(select(Photo).where(Photo.id == photo_id))
    photo = result.scalar_one_or_none()
    
    # Delete like
    await db.delete(like)
    
    # Decrement likes count
    if photo:
        photo.likes_count = max(0, photo.likes_count - 1)
    
    await db.commit()
    
    return {"message": "Photo unliked successfully"}


@router.get("/{photo_id}/download")
async def download_photo(
    photo_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Download photo file"""
    
    result = await db.execute(select(Photo).where(Photo.id == photo_id))
    photo = result.scalar_one_or_none()
    
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found"
        )
    
    return FileResponse(
        path=photo.file_path,
        filename=photo.file_name,
        media_type="application/octet-stream"
    )