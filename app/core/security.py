from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
import secrets
import string

from app.core.config import settings

# Argon2 password hasher
ph = PasswordHasher()


# Password hashing
def hash_password(password: str) -> str:
    """Hash password using Argon2"""
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    try:
        ph.verify(hashed_password, plain_password)
        # Check if rehashing is needed
        if ph.check_needs_rehash(hashed_password):
            return True  # Password is valid, but should be rehashed
        return True
    except VerifyMismatchError:
        return False


# JWT Token functions
def create_access_token(data: Dict[str, Any]) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    # Ensure sub is a string as per JWT standard
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create JWT refresh token"""
    to_encode = data.copy()
    # Ensure sub is a string as per JWT standard
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and verify JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


# Verification code generation
def generate_verification_code() -> str:
    """Generate 6-digit verification code"""
    return ''.join(secrets.choice(string.digits) for _ in range(6))


def generate_verification_token() -> str:
    """Generate random token for password reset"""
    return secrets.token_urlsafe(32)