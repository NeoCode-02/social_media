from PIL import Image
import os
import uuid
from typing import Tuple
from fastapi import UploadFile, HTTPException, status
from app.core.config import settings


async def validate_image(file: UploadFile) -> None:
    """Validate uploaded image file"""
    
    # Check file extension
    ext = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
    if ext not in settings.allowed_extensions_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: {', '.join(settings.allowed_extensions_list)}"
        )
    
    # Check file size
    content = await file.read()
    await file.seek(0)  # Reset file pointer
    
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE / 1024 / 1024}MB"
        )


async def save_upload_file(
    file: UploadFile,
    upload_dir: str = None,
    compress: bool = True
) -> Tuple[str, int, int, int]:
    """
    Save uploaded image file
    Returns: (file_path, file_size, width, height)
    """
    if upload_dir is None:
        upload_dir = settings.UPLOAD_DIR
    
    # Validate image
    await validate_image(file)
    
    # Generate unique filename
    ext = file.filename.split('.')[-1].lower()
    filename = f"{uuid.uuid4()}.{ext}"
    filepath = os.path.join(upload_dir, filename)
    
    # Ensure directory exists
    os.makedirs(upload_dir, exist_ok=True)
    
    # Read file content
    content = await file.read()
    
    # Open image with Pillow
    try:
        img = Image.open(file.file)
        
        # Get original dimensions
        width, height = img.size
        
        # Resize if too large
        if width > settings.MAX_IMAGE_WIDTH or height > settings.MAX_IMAGE_HEIGHT:
            img.thumbnail((settings.MAX_IMAGE_WIDTH, settings.MAX_IMAGE_HEIGHT), Image.Resampling.LANCZOS)
            width, height = img.size
        
        # Convert RGBA to RGB if needed (for JPEG)
        if img.mode == 'RGBA' and ext in ['jpg', 'jpeg']:
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])  # Use alpha channel as mask
            img = background
        
        # Save with compression
        if compress and ext in ['jpg', 'jpeg']:
            img.save(filepath, 'JPEG', quality=settings.IMAGE_QUALITY, optimize=True)
        elif compress and ext == 'png':
            img.save(filepath, 'PNG', optimize=True)
        else:
            img.save(filepath)
        
        # Get file size
        file_size = os.path.getsize(filepath)
        
        return filepath, file_size, width, height
        
    except Exception as e:
        # If image processing fails, save as is
        with open(filepath, 'wb') as f:
            f.write(content)
        
        file_size = len(content)
        return filepath, file_size, None, None


def delete_file(filepath: str) -> None:
    """Delete file if exists"""
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except Exception:
            pass


def get_file_url(filepath: str) -> str:
    """Get public URL for file"""
    return f"{settings.BACKEND_URL}/{filepath}"