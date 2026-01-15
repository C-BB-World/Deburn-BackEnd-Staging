"""
Email service for sending transactional emails.

Supports SMTP, Resend API, and console logging modes.
"""

import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

import httpx
import aiosmtplib

logger = logging.getLogger(__name__)


class EmailService:
    """
    Email service with multi-mode support.

    Modes:
        - console: Log emails to console (development)
        - smtp: Send via SMTP (e.g., Resend SMTP relay)
        - resend: Send via Resend HTTP API
    """

    RESEND_API_URL = "https://api.resend.com/emails"

    def __init__(
        self,
        mode: Optional[str] = None,
        resend_api_key: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: str = "Deburn",
        app_url: Optional[str] = None,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
    ):
        """
        Initialize email service.

        Args:
            mode: "console", "smtp", or "resend" (default from EMAIL_MODE env var)
            resend_api_key: Resend API key (default from RESEND_API_KEY env var)
            from_email: Sender email address
            from_name: Sender display name
            app_url: Base URL for links in emails
            smtp_host: SMTP server host
            smtp_port: SMTP server port
            smtp_user: SMTP username
            smtp_password: SMTP password
        """
        self._mode = mode or os.environ.get("EMAIL_MODE", "console")
        self._from_email = from_email or os.environ.get("SMTP_FROM_EMAIL", "noreply@example.com")
        self._from_name = from_name or os.environ.get("SMTP_FROM_NAME", "Deburn")
        self._app_url = app_url or os.environ.get("APP_URL", "http://localhost:3000")

        # Resend API key (can use SMTP_PASSWORD as fallback for existing configs)
        self._resend_api_key = (
            resend_api_key
            or os.environ.get("RESEND_API_KEY")
            or os.environ.get("SMTP_PASSWORD")
        )

        # SMTP settings (for actual SMTP mode)
        self._smtp_host = smtp_host or os.environ.get("SMTP_HOST")
        self._smtp_port = smtp_port or int(os.environ.get("SMTP_PORT", "465"))
        self._smtp_user = smtp_user or os.environ.get("SMTP_USER", "resend")
        self._smtp_password = smtp_password or os.environ.get("SMTP_PASSWORD")

        # Normalize mode: if smtp mode with Resend API key, use Resend HTTP API
        if self._mode == "smtp" and self._resend_api_key:
            logger.info("EMAIL_MODE=smtp with Resend API key detected, using Resend HTTP API")
            self._mode = "resend"
        elif self._mode == "resend" and not self._resend_api_key:
            logger.warning("Resend API key not configured, falling back to console mode")
            self._mode = "console"
        elif self._mode == "smtp" and not self._smtp_host:
            logger.warning("SMTP host not configured, falling back to console mode")
            self._mode = "console"

        logger.info(f"Email service initialized in {self._mode} mode")

    async def send_verification_email(
        self,
        to_email: str,
        verification_link: str,
        user_name: Optional[str] = None,
    ) -> dict:
        """
        Send email verification email.

        Args:
            to_email: Recipient email address
            verification_link: Firebase verification link
            user_name: User's display name (optional)

        Returns:
            dict with success status and message
        """
        name = user_name or "there"
        subject = "Verify your email address"

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 40px 20px; }}
        .button {{ display: inline-block; background: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
        .footer {{ margin-top: 40px; color: #666; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Verify your email</h1>
        <p>Hi {name},</p>
        <p>Thanks for signing up! Please verify your email address by clicking the button below:</p>
        <a href="{verification_link}" class="button">Verify Email</a>
        <p>Or copy and paste this link into your browser:</p>
        <p style="word-break: break-all; color: #666;">{verification_link}</p>
        <p>If you didn't create an account, you can safely ignore this email.</p>
        <div class="footer">
            <p>Best regards,<br>The Deburn Team</p>
        </div>
    </div>
</body>
</html>
"""

        text_content = f"""
Verify your email

Hi {name},

Thanks for signing up! Please verify your email address by clicking the link below:

{verification_link}

If you didn't create an account, you can safely ignore this email.

Best regards,
The Deburn Team
"""

        return await self._send(
            to=to_email,
            subject=subject,
            html=html_content,
            text=text_content,
        )

    async def send_password_reset_email(
        self,
        to_email: str,
        reset_link: str,
        user_name: Optional[str] = None,
    ) -> dict:
        """
        Send password reset email.

        Args:
            to_email: Recipient email address
            reset_link: Firebase password reset link
            user_name: User's display name (optional)

        Returns:
            dict with success status and message
        """
        name = user_name or "there"
        subject = "Reset your password"

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 40px 20px; }}
        .button {{ display: inline-block; background: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
        .footer {{ margin-top: 40px; color: #666; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Reset your password</h1>
        <p>Hi {name},</p>
        <p>We received a request to reset your password. Click the button below to create a new password:</p>
        <a href="{reset_link}" class="button">Reset Password</a>
        <p>Or copy and paste this link into your browser:</p>
        <p style="word-break: break-all; color: #666;">{reset_link}</p>
        <p>If you didn't request a password reset, you can safely ignore this email.</p>
        <div class="footer">
            <p>Best regards,<br>The Deburn Team</p>
        </div>
    </div>
</body>
</html>
"""

        text_content = f"""
Reset your password

Hi {name},

We received a request to reset your password. Click the link below to create a new password:

{reset_link}

If you didn't request a password reset, you can safely ignore this email.

Best regards,
The Deburn Team
"""

        return await self._send(
            to=to_email,
            subject=subject,
            html=html_content,
            text=text_content,
        )

    async def _send(
        self,
        to: str,
        subject: str,
        html: str,
        text: str,
    ) -> dict:
        """
        Send email via configured provider.

        Args:
            to: Recipient email
            subject: Email subject
            html: HTML content
            text: Plain text content

        Returns:
            dict with success status and details
        """
        if self._mode == "console":
            return self._send_console(to, subject, html, text)
        elif self._mode == "smtp":
            return await self._send_smtp(to, subject, html, text)
        elif self._mode == "resend":
            return await self._send_resend(to, subject, html, text)
        else:
            logger.error(f"Unknown email mode: {self._mode}")
            return {"success": False, "error": f"Unknown email mode: {self._mode}"}

    def _send_console(
        self,
        to: str,
        subject: str,
        html: str,
        text: str,
    ) -> dict:
        """Log email to console (development mode)."""
        logger.info("=" * 60)
        logger.info("EMAIL (console mode)")
        logger.info(f"To: {to}")
        logger.info(f"Subject: {subject}")
        logger.info("-" * 60)
        logger.info(text)
        logger.info("=" * 60)

        return {
            "success": True,
            "mode": "console",
            "message": "Email logged to console",
        }

    async def _send_smtp(
        self,
        to: str,
        subject: str,
        html: str,
        text: str,
    ) -> dict:
        """Send email via SMTP."""
        try:
            # Create multipart message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self._from_name} <{self._from_email}>"
            message["To"] = to

            # Attach plain text and HTML parts
            part1 = MIMEText(text, "plain")
            part2 = MIMEText(html, "html")
            message.attach(part1)
            message.attach(part2)

            # Determine if we should use SSL (port 465) or STARTTLS (port 587)
            use_tls = self._smtp_port == 465

            # Send via SMTP
            await aiosmtplib.send(
                message,
                hostname=self._smtp_host,
                port=self._smtp_port,
                username=self._smtp_user,
                password=self._smtp_password,
                use_tls=use_tls,
                start_tls=not use_tls,
            )

            logger.info(f"Email sent via SMTP to {to}")
            return {
                "success": True,
                "mode": "smtp",
                "message": "Email sent via SMTP",
            }

        except Exception as e:
            logger.error(f"Failed to send email via SMTP: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    async def _send_resend(
        self,
        to: str,
        subject: str,
        html: str,
        text: str,
    ) -> dict:
        """Send email via Resend API."""
        if not self._resend_api_key:
            return {"success": False, "error": "Resend API key not configured"}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.RESEND_API_URL,
                    headers={
                        "Authorization": f"Bearer {self._resend_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "from": f"{self._from_name} <{self._from_email}>",
                        "to": [to],
                        "subject": subject,
                        "html": html,
                        "text": text,
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "mode": "resend",
                        "messageId": data.get("id"),
                    }
                else:
                    error_data = response.json()
                    error_msg = error_data.get("message", "Unknown error")
                    logger.error(f"Resend API error: {error_msg}")
                    return {
                        "success": False,
                        "error": error_msg,
                    }

            except Exception as e:
                logger.error(f"Failed to send email via Resend: {e}")
                return {
                    "success": False,
                    "error": str(e),
                }
