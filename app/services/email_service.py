import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from app.core.config import settings


async def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None
):
    """Send email via SMTP"""
    message = MIMEMultipart("alternative")
    message["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
    message["To"] = to_email
    message["Subject"] = subject
    
    # Add text and HTML parts
    if text_content:
        text_part = MIMEText(text_content, "plain")
        message.attach(text_part)
    
    html_part = MIMEText(html_content, "html")
    message.attach(html_part)
    
    # Send email
    await aiosmtplib.send(
        message,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USER,
        password=settings.SMTP_PASSWORD,
        start_tls=True,
    )


def get_verification_email_html(code: str, username: str) -> str:
    """Generate verification email HTML"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .code {{ font-size: 32px; font-weight: bold; color: #4F46E5; letter-spacing: 5px; 
                     text-align: center; padding: 20px; background: #F3F4F6; border-radius: 8px; }}
            .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Welcome to {settings.APP_NAME}!</h2>
            <p>Hi {username},</p>
            <p>Thank you for registering. Please verify your email address using the code below:</p>
            <div class="code">{code}</div>
            <p>This code will expire in {settings.VERIFICATION_CODE_EXPIRE_MINUTES} minutes.</p>
            <p>If you didn't create an account, please ignore this email.</p>
            <div class="footer">
                <p>Best regards,<br>{settings.APP_NAME} Team</p>
            </div>
        </div>
    </body>
    </html>
    """


def get_password_reset_email_html(reset_link: str, username: str) -> str:
    """Generate password reset email HTML"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .button {{ display: inline-block; padding: 12px 24px; background: #4F46E5; 
                      color: white; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
            .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Password Reset Request</h2>
            <p>Hi {username},</p>
            <p>We received a request to reset your password. Click the button below to reset it:</p>
            <a href="{reset_link}" class="button">Reset Password</a>
            <p>Or copy and paste this link into your browser:</p>
            <p style="word-break: break-all; color: #4F46E5;">{reset_link}</p>
            <p>This link will expire in 30 minutes.</p>
            <p>If you didn't request a password reset, please ignore this email.</p>
            <div class="footer">
                <p>Best regards,<br>{settings.APP_NAME} Team</p>
            </div>
        </div>
    </body>
    </html>
    """


def get_welcome_email_html(username: str) -> str:
    """Generate welcome email HTML"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Welcome to {settings.APP_NAME}! 🎉</h2>
            <p>Hi {username},</p>
            <p>Your email has been verified successfully! You can now enjoy all features of our platform:</p>
            <ul>
                <li>Upload and share photos</li>
                <li>Follow other users</li>
                <li>Like and comment on photos</li>
                <li>Chat with other users</li>
            </ul>
            <p>Start exploring and sharing your amazing photos!</p>
            <div class="footer">
                <p>Best regards,<br>{settings.APP_NAME} Team</p>
            </div>
        </div>
    </body>
    </html>
    """