from app.core.celery_app import celery_app
from app.services.email_service import (
    send_email,
    get_verification_email_html,
    get_password_reset_email_html,
    get_welcome_email_html
)
from datetime import datetime, timedelta
import asyncio


def run_async(coro):
    """Helper to run async functions in Celery"""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


@celery_app.task(name="app.tasks.email_tasks.send_verification_email")
def send_verification_email(email: str, username: str, code: str):
    """Send verification email task"""
    html_content = get_verification_email_html(code, username)
    text_content = f"Your verification code is: {code}"
    
    run_async(send_email(
        to_email=email,
        subject="Verify your email",
        html_content=html_content,
        text_content=text_content
    ))


@celery_app.task(name="app.tasks.email_tasks.send_welcome_email")
def send_welcome_email(email: str, username: str):
    """Send welcome email task"""
    html_content = get_welcome_email_html(username)
    
    run_async(send_email(
        to_email=email,
        subject="Welcome to Photo Social Platform!",
        html_content=html_content
    ))


@celery_app.task(name="app.tasks.email_tasks.send_password_reset_email")
def send_password_reset_email(email: str, username: str, reset_link: str):
    """Send password reset email task"""
    html_content = get_password_reset_email_html(reset_link, username)
    
    run_async(send_email(
        to_email=email,
        subject="Password Reset Request",
        html_content=html_content
    ))


@celery_app.task(name="app.tasks.email_tasks.clean_old_chat_messages")
def clean_old_chat_messages():
    """
    Clean chat messages older than 1 year
    This task runs daily via Celery Beat
    """
    from app.db.session import AsyncSessionLocal
    from app.models.chat import ChatMessage
    from sqlalchemy import delete
    from app.core.config import settings
    
    async def clean():
        async with AsyncSessionLocal() as db:
            cutoff_date = datetime.utcnow() - timedelta(days=settings.CHAT_MESSAGE_RETENTION_DAYS)
            
            await db.execute(
                delete(ChatMessage).where(ChatMessage.created_at < cutoff_date)
            )
            await db.commit()
    
    run_async(clean())
    return "Old chat messages cleaned"