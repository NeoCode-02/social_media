from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from authlib.integrations.starlette_client import OAuth
from starlette.requests import Request

from app.db.session import get_db
from app.models.user import User, EmailVerification, PasswordReset
from app.schemas.user import UserRegister, UserResponse, EmailVerificationRequest, ResendVerificationRequest, UserLogin, ForgotPasswordRequest, ResetPasswordRequest
from app.schemas.token import LoginResponse, RefreshTokenRequest
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token, generate_verification_code, generate_verification_token
from app.core.config import settings
from app.tasks.email_tasks import send_verification_email, send_welcome_email, send_password_reset_email
from app.api.deps import get_current_user

router = APIRouter()

# OAuth setup
oauth = OAuth()
oauth.register(
    name='google',
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)


@router.get("/test-auth")
async def test_auth(current_user: User = Depends(get_current_user)):
    """Test endpoint to verify authentication is working"""
    return {
        "message": "Authentication successful!",
        "user_id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "is_verified": current_user.is_verified
    }


@router.post("/register", response_model=dict)
async def register(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user and send verification email"""
    
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if username already exists
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Create user
    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        is_verified=False
    )
    db.add(user)
    await db.flush()
    
    # Generate verification code
    code = generate_verification_code()
    verification = EmailVerification(
        user_id=user.id,
        email=user.email,
        code=code,
        expires_at=datetime.utcnow() + timedelta(minutes=settings.VERIFICATION_CODE_EXPIRE_MINUTES)
    )
    db.add(verification)
    await db.commit()
    
    # Send verification email asynchronously
    send_verification_email.delay(user.email, user.username, code)
    
    return {
        "message": "Registration successful. Please check your email for verification code.",
        "email": user.email
    }


@router.post("/verify-email", response_model=dict)
async def verify_email(
    verification_data: EmailVerificationRequest,
    db: AsyncSession = Depends(get_db)
):
    """Verify email with 6-digit code"""
    
    # Find verification record
    result = await db.execute(
        select(EmailVerification)
        .where(
            EmailVerification.email == verification_data.email,
            EmailVerification.code == verification_data.code,
            EmailVerification.is_used == False,
            EmailVerification.expires_at > datetime.utcnow()
        )
    )
    verification = result.scalar_one_or_none()
    
    if not verification:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code"
        )
    
    # Get user
    result = await db.execute(select(User).where(User.id == verification.user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Mark user as verified
    user.is_verified = True
    verification.is_used = True
    await db.commit()
    
    # Send welcome email
    send_welcome_email.delay(user.email, user.username)
    
    return {
        "message": "Email verified successfully! You can now login.",
        "email": user.email
    }


@router.post("/resend-verification", response_model=dict)
async def resend_verification(
    data: ResendVerificationRequest,
    db: AsyncSession = Depends(get_db)
):
    """Resend verification code"""
    
    # Get user
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified"
        )
    
    # Mark old verifications as used
    await db.execute(
        select(EmailVerification)
        .where(EmailVerification.email == data.email)
    )
    
    # Generate new code
    code = generate_verification_code()
    verification = EmailVerification(
        user_id=user.id,
        email=user.email,
        code=code,
        expires_at=datetime.utcnow() + timedelta(minutes=settings.VERIFICATION_CODE_EXPIRE_MINUTES)
    )
    db.add(verification)
    await db.commit()
    
    # Send email
    send_verification_email.delay(user.email, user.username, code)
    
    return {"message": "Verification code sent"}


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """Login with email and password"""
    
    # Get user
    result = await db.execute(select(User).where(User.email == login_data.email))
    user = result.scalar_one_or_none()
    
    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Verify password
    if not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )
    
    # Create tokens
    access_token = create_access_token({"sub": user.id})
    refresh_token = create_refresh_token({"sub": user.id})
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


@router.post("/refresh", response_model=dict)
async def refresh_token(
    token_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token"""
    
    payload = decode_token(token_data.refresh_token)
    
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("sub")
    
    # Convert user_id to int if it's a string (from JWT)
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Verify user exists
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user"
        )
    
    # Create new access token
    access_token = create_access_token({"sub": user.id})
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.post("/forgot-password", response_model=dict)
async def forgot_password(
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """Request password reset"""
    
    # Get user
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    
    # Always return success to prevent email enumeration
    if not user:
        return {"message": "If the email exists, a password reset link has been sent"}
    
    # Generate reset token
    token = generate_verification_token()
    reset = PasswordReset(
        user_id=user.id,
        email=user.email,
        token=token,
        expires_at=datetime.utcnow() + timedelta(minutes=30)
    )
    db.add(reset)
    await db.commit()
    
    # Send email
    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    send_password_reset_email.delay(user.email, user.username, reset_link)
    
    return {"message": "If the email exists, a password reset link has been sent"}


@router.post("/reset-password", response_model=dict)
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """Reset password using token"""
    
    # Find reset record
    result = await db.execute(
        select(PasswordReset)
        .where(
            PasswordReset.token == data.token,
            PasswordReset.is_used == False,
            PasswordReset.expires_at > datetime.utcnow()
        )
    )
    reset = result.scalar_one_or_none()
    
    if not reset:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Get user
    result = await db.execute(select(User).where(User.id == reset.user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update password
    user.hashed_password = hash_password(data.new_password)
    reset.is_used = True
    await db.commit()
    
    return {"message": "Password reset successful"}


@router.get("/google")
async def google_login(request: Request):
    """Initiate Google OAuth login"""
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Google OAuth callback"""
    
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')
        
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user info from Google"
            )
        
        email = user_info.get('email')
        name = user_info.get('name', email.split('@')[0])
        
        # Check if user exists
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        if not user:
            # Create new user
            # Generate unique username
            base_username = name.lower().replace(' ', '_')
            username = base_username
            counter = 1
            while True:
                result = await db.execute(select(User).where(User.username == username))
                if not result.scalar_one_or_none():
                    break
                username = f"{base_username}{counter}"
                counter += 1
            
            user = User(
                username=username,
                email=email,
                is_verified=True,  # Google email is already verified
                is_oauth=True,
                oauth_provider='google'
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
        
        # Create tokens
        access_token = create_access_token({"sub": user.id})
        refresh_token = create_refresh_token({"sub": user.id})
        
        # Redirect to frontend with tokens
        redirect_url = f"{settings.FRONTEND_URL}/auth/callback?access_token={access_token}&refresh_token={refresh_token}"
        return RedirectResponse(url=redirect_url)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth authentication failed: {str(e)}"
        )