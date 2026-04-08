import httpx
import structlog

from app.config import settings

logger = structlog.get_logger()


async def send_email(to: str, subject: str, html_body: str) -> None:
    if settings.ENVIRONMENT != "production":
        logger.info("email_dev_mode", to=to, subject=subject, body_preview=html_body[:200])
        return

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": settings.RESEND_FROM_EMAIL,
                "to": [to],
                "subject": subject,
                "html": html_body,
            },
        )
        if response.status_code not in (200, 201):
            logger.error("email_send_failed", status=response.status_code, body=response.text)
            raise RuntimeError(f"Failed to send email: {response.status_code}")
        logger.info("email_sent", to=to, subject=subject)


async def send_verification_email(to: str, token: str) -> None:
    link = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    html = f"""
    <h2>Verify your email</h2>
    <p>Click the link below to verify your email address:</p>
    <p><a href="{link}">Verify Email</a></p>
    <p>This link expires in 24 hours.</p>
    <p>If you didn't create an account, you can ignore this email.</p>
    """
    await send_email(to, "Verify your email — ServiceTracks", html)


async def send_password_reset_email(to: str, token: str) -> None:
    link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    html = f"""
    <h2>Reset your password</h2>
    <p>Click the link below to reset your password:</p>
    <p><a href="{link}">Reset Password</a></p>
    <p>This link expires in 1 hour.</p>
    <p>If you didn't request a password reset, you can ignore this email.</p>
    """
    await send_email(to, "Reset your password — ServiceTracks", html)
