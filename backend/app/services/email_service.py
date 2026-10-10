"""Optional SMTP; logs reset links when mail is not configured."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.config import PUBLIC_APP_URL, SMTP_FROM, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USER

logger = logging.getLogger(__name__)


def reset_link(raw_token: str) -> str:
    return f"{PUBLIC_APP_URL.rstrip('/')}/reset-password?token={raw_token}"


def send_password_reset(email: str, raw_token: str) -> None:
    link = reset_link(raw_token)
    body = f"Reset your Clipseek password:\n{link}\n\nThis link expires in 1 hour."
    if not SMTP_HOST:
        logger.warning("SMTP not configured; password reset for %s: %s", email, link)
        return
    msg = EmailMessage()
    msg["Subject"] = "Reset your Clipseek password"
    msg["From"] = SMTP_FROM
    msg["To"] = email
    msg.set_content(body)
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as smtp:
        smtp.starttls()
        if SMTP_USER:
            smtp.login(SMTP_USER, SMTP_PASSWORD)
        smtp.send_message(msg)
