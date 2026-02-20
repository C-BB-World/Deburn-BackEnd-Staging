"""
Email service for sending transactional emails.

Supports SMTP, Resend API, and console logging modes.
Supports i18n via JSON locale files.
"""

import json
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Optional

import httpx
import aiosmtplib

from config.email_config import (
    RESEND_API_URL,
    RESEND_BATCH_API_URL,
    EMAIL_MAX_BATCH_SIZE,
    EMAIL_DEFAULTS,
)

logger = logging.getLogger(__name__)

# Load locale files
LOCALES_DIR = Path(__file__).parent / "locales"
_translations_cache: dict = {}


class EmailService:
    """
    Email service with multi-mode support.

    Modes:
        - console: Log emails to console (development)
        - smtp: Send via SMTP (e.g., Resend SMTP relay)
        - resend: Send via Resend HTTP API
    """

    def __init__(
        self,
        mode: Optional[str] = None,
        resend_api_key: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: str = "Human First AI",
        team_name: Optional[str] = None,
        app_url: Optional[str] = None,
        api_url: Optional[str] = None,
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
            team_name: Team name for email signatures
            app_url: Base URL for frontend links in emails
            api_url: Base URL for API links in emails (for redirects)
            smtp_host: SMTP server host
            smtp_port: SMTP server port
            smtp_user: SMTP username
            smtp_password: SMTP password
        """
        self._mode = mode or os.environ.get("EMAIL_MODE", "console")
        self._from_email = from_email or os.environ.get("SMTP_FROM_EMAIL", "noreply@example.com")
        self._from_name = from_name or os.environ.get("SMTP_FROM_NAME", "Human First AI")
        self._team_name = team_name or os.environ.get("EMAIL_TEAM_NAME", "The Human First AI Team")
        self._app_url = app_url or os.environ.get("APP_URL", "http://localhost:3000")
        self._api_url = api_url or os.environ.get("API_URL", "http://localhost:8000")

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

    def _get_translations(
        self,
        lang: str,
        email_type: str,
        variables: dict
    ) -> dict:
        """
        Load translations from JSON file and replace placeholders.

        Args:
            lang: Language code ("en" or "sv")
            email_type: Email type key (e.g., "verification", "meeting_scheduled")
            variables: Dict of placeholder values to substitute

        Returns:
            dict with all translated strings for the email type
        """
        global _translations_cache

        # Fallback to English if language not supported
        if lang not in ["en", "sv"]:
            lang = "en"

        # Load from cache or file
        if lang not in _translations_cache:
            locale_file = LOCALES_DIR / f"{lang}.json"
            try:
                with open(locale_file, "r", encoding="utf-8") as f:
                    _translations_cache[lang] = json.load(f)
            except FileNotFoundError:
                logger.warning(f"Locale file not found: {locale_file}, falling back to English")
                lang = "en"
                locale_file = LOCALES_DIR / "en.json"
                with open(locale_file, "r", encoding="utf-8") as f:
                    _translations_cache[lang] = json.load(f)

        # Get translations for this email type
        translations = _translations_cache.get(lang, {}).get(email_type, {})

        # Replace placeholders in each string
        result = {}
        for key, value in translations.items():
            if isinstance(value, str):
                for var_name, var_value in variables.items():
                    value = value.replace(f"{{{{{var_name}}}}}", str(var_value))
            result[key] = value

        return result

    async def send_verification_email(
        self,
        to_email: str,
        verification_link: str,
        user_name: Optional[str] = None,
        language: str = "en",
    ) -> dict:
        """
        Send email verification email.

        Args:
            to_email: Recipient email address
            verification_link: Firebase verification link
            user_name: User's display name (optional)
            language: Language code ("en" or "sv")

        Returns:
            dict with success status and message
        """
        name = user_name or "there"

        # Get translations
        t = self._get_translations(language, "verification", {"name": name})

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <!--[if mso]>
    <style type="text/css">
        body, table, td {{font-family: Arial, Helvetica, sans-serif !important;}}
    </style>
    <![endif]-->
</head>
<body style="margin: 0; padding: 0; background-color: #f5f5f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; line-height: 1.6; color: #333333;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color: #f5f5f5;">
        <tr>
            <td align="center" style="padding: 20px 0;">
                <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; max-width: 600px;">
                    <!-- Header -->
                    <tr>
                        <td align="center" bgcolor="#2D4A47" style="background-color: #2D4A47; padding: 40px 20px;">
                            <h1 style="margin: 0; font-size: 28px; color: #ffffff; font-weight: 600;">{t.get("header", "Verify your email")}</h1>
                        </td>
                    </tr>
                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px 30px;">
                            <p style="margin: 0 0 16px 0; font-size: 16px; color: #333333;">{t.get("greeting", f"Hi {name},")}</p>
                            <p style="margin: 0 0 24px 0; font-size: 16px; color: #333333;">{t.get("body", "Thanks for signing up! Please verify your email address by clicking the button below:")}</p>

                            <!-- Button -->
                            <table role="presentation" cellpadding="0" cellspacing="0" style="margin: 24px auto;">
                                <tr>
                                    <td align="center" bgcolor="#2D4A47" style="background-color: #2D4A47; border-radius: 8px;">
                                        <a href="{verification_link}" target="_blank" style="display: inline-block; padding: 14px 28px; font-size: 16px; font-weight: 600; color: #ffffff; text-decoration: none;">{t.get("button", "Verify Email")}</a>
                                    </td>
                                </tr>
                            </table>

                            <p style="margin: 24px 0 8px 0; font-size: 14px; color: #666666;">{t.get("link_fallback", "Or copy and paste this link into your browser:")}</p>
                            <p style="margin: 0 0 24px 0; font-size: 14px; color: #2D4A47; word-break: break-all;">{verification_link}</p>
                            <p style="margin: 0; font-size: 16px; color: #333333;">{t.get("ignore_notice", "If you didn't create an account, you can safely ignore this email.")}</p>
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 20px 30px; border-top: 1px solid #eeeeee;">
                            <p style="margin: 0; font-size: 14px; color: #666666; text-align: center;">{t.get("sign_off", "Best regards,")}<br>{self._team_name}</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""

        text_content = f"""
{t.get("header", "Verify your email")}

{t.get("greeting", f"Hi {name},")}

{t.get("body", "Thanks for signing up! Please verify your email address by clicking the link below:")}

{verification_link}

{t.get("ignore_notice", "If you didn't create an account, you can safely ignore this email.")}

{t.get("sign_off", "Best regards,")}
{self._team_name}
"""

        return await self._send(
            to=to_email,
            subject=t.get("subject", "Verify your email address"),
            html=html_content,
            text=text_content,
        )

    async def send_circle_invitation_email(
        self,
        to_email: str,
        token: str,
        pool_name: str,
        topic: Optional[str] = None,
        custom_message: Optional[str] = None,
        first_name: Optional[str] = None,
        expires_at: Optional[str] = None,
        language: str = "en",
    ) -> dict:
        """
        Send circle invitation email.

        Args:
            to_email: Recipient email address
            token: Unique invitation token
            pool_name: Name of the circle pool
            topic: Discussion topic (optional)
            custom_message: Custom message from inviter (optional)
            first_name: Invitee's first name (optional)
            expires_at: Expiration date string (optional)
            language: Language code ("en" or "sv")

        Returns:
            dict with success status and message
        """
        name = first_name or "there"

        # Get translations
        t = self._get_translations(language, "circle_invitation", {
            "name": name,
            "pool_name": pool_name,
            "expires_at": expires_at or ""
        })

        accept_link = f"{self._api_url}/api/circles/invitations/{token}/accept"
        decline_link = f"{self._api_url}/api/circles/invitations/{token}/decline"

        # Build topic section
        topic_html = ""
        topic_text = ""
        if topic:
            topic_label = t.get("topic_label", "Topic:")
            topic_html = f'<p style="margin: 16px 0 0 0; font-size: 16px; color: #666666;"><strong>{topic_label}</strong> {topic}</p>'
            topic_text = f"\n{topic_label} {topic}"

        # Build custom message section
        message_html = ""
        message_text = ""
        if custom_message:
            message_html = f'''
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin: 20px 0;">
                                <tr>
                                    <td bgcolor="#f5f5f5" style="background-color: #f5f5f5; padding: 16px; border-radius: 8px;">
                                        <p style="margin: 0; font-size: 16px; font-style: italic; color: #333333;">"{custom_message}"</p>
                                    </td>
                                </tr>
                            </table>'''
            message_text = f'\n\nMessage from the inviter:\n"{custom_message}"'

        # Build expiry section
        expiry_html = ""
        expiry_text = ""
        if expires_at:
            expiry_notice = t.get("expiry_notice", f"This invitation expires on {expires_at}.")
            expiry_html = f'<p style="margin: 20px 0 0 0; font-size: 14px; color: #999999;">{expiry_notice}</p>'
            expiry_text = f"\n\n{expiry_notice}"

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <!--[if mso]>
    <style type="text/css">
        body, table, td {{font-family: Arial, Helvetica, sans-serif !important;}}
    </style>
    <![endif]-->
</head>
<body style="margin: 0; padding: 0; background-color: #f5f5f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; line-height: 1.6; color: #333333;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color: #f5f5f5;">
        <tr>
            <td align="center" style="padding: 20px 0;">
                <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; max-width: 600px;">
                    <!-- Header -->
                    <tr>
                        <td align="center" bgcolor="#2D4A47" style="background-color: #2D4A47; padding: 40px 20px;">
                            <h1 style="margin: 0; font-size: 28px; color: #ffffff; font-weight: 600;">{t.get("header", "You're Invited!")}</h1>
                        </td>
                    </tr>
                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px 30px;">
                            <p style="margin: 0 0 16px 0; font-size: 16px; color: #333333;">{t.get("greeting", f"Hi {name},")}</p>
                            <p style="margin: 0 0 16px 0; font-size: 16px; color: #333333;">{t.get("body", f"You've been invited to join <strong>{pool_name}</strong>, where you'll connect with peers for meaningful conversations and mutual support.")}</p>
                            {topic_html}
                            {message_html}

                            <!-- Buttons -->
                            <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="margin: 30px 0;">
                                <tr>
                                    <td align="center">
                                        <table role="presentation" cellpadding="0" cellspacing="0">
                                            <tr>
                                                <td align="center" bgcolor="#2D4A47" style="background-color: #2D4A47; border-radius: 8px;">
                                                    <a href="{accept_link}" target="_blank" style="display: inline-block; padding: 14px 28px; font-size: 16px; font-weight: 600; color: #ffffff; text-decoration: none;">{t.get("accept_button", "Accept Invitation")}</a>
                                                </td>
                                                <td width="20"></td>
                                                <td align="center" bgcolor="#e5e7eb" style="background-color: #e5e7eb; border-radius: 8px;">
                                                    <a href="{decline_link}" target="_blank" style="display: inline-block; padding: 14px 28px; font-size: 16px; font-weight: 600; color: #374151; text-decoration: none;">{t.get("decline_button", "Decline")}</a>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>

                            <p style="margin: 24px 0 8px 0; font-size: 14px; color: #666666;">{t.get("link_fallback", "Or copy and paste this link into your browser:")}</p>
                            <p style="margin: 0 0 16px 0; font-size: 14px; color: #2D4A47; word-break: break-all;">{accept_link}</p>
                            {expiry_html}
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 20px 30px; border-top: 1px solid #eeeeee;">
                            <p style="margin: 0; font-size: 14px; color: #666666; text-align: center;">{t.get("sign_off", "Best regards,")}<br>{self._team_name}</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""

        text_content = f"""
{t.get("header", "You're Invited!")}

{t.get("greeting", f"Hi {name},")}

{t.get("body", f"You've been invited to join {pool_name}, where you'll connect with peers for meaningful conversations and mutual support.")}
{topic_text}
{message_text}

{t.get("accept_button", "Accept Invitation")}: {accept_link}

{t.get("decline_button", "Decline")}: {decline_link}
{expiry_text}

{t.get("sign_off", "Best regards,")}
{self._team_name}
"""

        return await self._send(
            to=to_email,
            subject=t.get("subject", f"You're invited to join {pool_name}"),
            html=html_content,
            text=text_content,
        )

    async def send_member_moved_email(
        self,
        to_email: str,
        user_name: Optional[str] = None,
        from_group_name: str = "",
        to_group_name: str = "",
        pool_name: str = "",
        language: str = "en",
    ) -> dict:
        """
        Send notification email when a member is moved between groups.

        Args:
            to_email: Recipient email address
            user_name: User's display name (optional)
            from_group_name: Name of the source group
            to_group_name: Name of the target group
            pool_name: Name of the pool
            language: Language code ("en" or "sv")

        Returns:
            dict with success status and message
        """
        name = user_name or "there"

        # Get translations
        t = self._get_translations(language, "member_moved", {
            "name": name,
            "to_group": to_group_name,
            "pool_name": pool_name
        })

        circles_link = f"{self._app_url}/circles"

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <!--[if mso]>
    <style type="text/css">
        body, table, td {{font-family: Arial, Helvetica, sans-serif !important;}}
    </style>
    <![endif]-->
</head>
<body style="margin: 0; padding: 0; background-color: #f5f5f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; line-height: 1.6; color: #333333;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color: #f5f5f5;">
        <tr>
            <td align="center" style="padding: 20px 0;">
                <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; max-width: 600px;">
                    <!-- Header -->
                    <tr>
                        <td align="center" bgcolor="#2D4A47" style="background-color: #2D4A47; padding: 40px 20px;">
                            <h1 style="margin: 0; font-size: 28px; color: #ffffff; font-weight: 600;">{t.get("header", "Group Change Notice")}</h1>
                        </td>
                    </tr>
                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px 30px;">
                            <p style="margin: 0 0 16px 0; font-size: 16px; color: #333333;">{t.get("greeting", f"Hi {name},")}</p>
                            <p style="margin: 0 0 24px 0; font-size: 16px; color: #333333;">{t.get("body", f"You've been moved to a new group in <strong>{pool_name}</strong>.")}</p>

                            <!-- Info Box -->
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin: 20px 0;">
                                <tr>
                                    <td bgcolor="#f5f5f5" style="background-color: #f5f5f5; padding: 20px; border-radius: 8px;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                                            <tr>
                                                <td style="padding: 8px 0; font-size: 14px; color: #666666;">{t.get("previous_label", "Previous Group:")}</td>
                                                <td align="right" style="padding: 8px 0; font-size: 14px; font-weight: 600; color: #333333;">{from_group_name}</td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 8px 0; font-size: 14px; color: #666666;">{t.get("new_label", "New Group:")}</td>
                                                <td align="right" style="padding: 8px 0; font-size: 14px; font-weight: 600; color: #333333;">{to_group_name}</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>

                            <p style="margin: 0 0 24px 0; font-size: 16px; color: #333333;">{t.get("info", "Your new group members are looking forward to connecting with you. Visit your circles page to see your new group and schedule meetings.")}</p>

                            <!-- Button -->
                            <table role="presentation" cellpadding="0" cellspacing="0" style="margin: 24px auto;">
                                <tr>
                                    <td align="center" bgcolor="#2D4A47" style="background-color: #2D4A47; border-radius: 8px;">
                                        <a href="{circles_link}" target="_blank" style="display: inline-block; padding: 14px 28px; font-size: 16px; font-weight: 600; color: #ffffff; text-decoration: none;">{t.get("button", "View Your Circles")}</a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 20px 30px; border-top: 1px solid #eeeeee;">
                            <p style="margin: 0; font-size: 14px; color: #666666; text-align: center;">{t.get("sign_off", "Best regards,")}<br>{self._team_name}</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""

        text_content = f"""
{t.get("header", "Group Change Notice")}

{t.get("greeting", f"Hi {name},")}

{t.get("body", f"You've been moved to a new group in {pool_name}.")}

{t.get("previous_label", "Previous Group:")} {from_group_name}
{t.get("new_label", "New Group:")} {to_group_name}

{t.get("info", "Your new group members are looking forward to connecting with you. Visit your circles page to see your new group and schedule meetings.")}

{t.get("button", "View Your Circles")}: {circles_link}

{t.get("sign_off", "Best regards,")}
{self._team_name}
"""

        return await self._send(
            to=to_email,
            subject=t.get("subject", f"You've been moved to {to_group_name}"),
            html=html_content,
            text=text_content,
        )

    async def send_group_message_email(
        self,
        to_email: str,
        user_name: Optional[str] = None,
        sender_name: str = "",
        group_name: str = "",
        message_preview: str = "",
        language: str = "en",
    ) -> dict:
        """Send notification email when someone posts a message in a group."""
        name = user_name or "there"

        circles_link = f"{self._app_url}/circles"

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; background-color: #f5f5f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; line-height: 1.6; color: #333333;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color: #f5f5f5;">
        <tr>
            <td align="center" style="padding: 20px 0;">
                <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; max-width: 600px;">
                    <tr>
                        <td align="center" bgcolor="#2D4A47" style="background-color: #2D4A47; padding: 40px 20px;">
                            <h1 style="margin: 0; font-size: 28px; color: #ffffff; font-weight: 600;">New Group Message</h1>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 40px 30px;">
                            <p style="margin: 0 0 16px 0; font-size: 16px; color: #333333;">Hi {name},</p>
                            <p style="margin: 0 0 24px 0; font-size: 16px; color: #333333;"><strong>{sender_name}</strong> left a message in <strong>{group_name}</strong>:</p>
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin: 20px 0;">
                                <tr>
                                    <td bgcolor="#f5f5f5" style="background-color: #f5f5f5; padding: 20px; border-radius: 8px; border-left: 4px solid #2D4A47;">
                                        <p style="margin: 0; font-size: 15px; color: #333333; font-style: italic;">"{message_preview}"</p>
                                    </td>
                                </tr>
                            </table>
                            <table role="presentation" cellpadding="0" cellspacing="0" style="margin: 24px auto;">
                                <tr>
                                    <td align="center" bgcolor="#2D4A47" style="background-color: #2D4A47; border-radius: 8px;">
                                        <a href="{circles_link}" target="_blank" style="display: inline-block; padding: 14px 28px; font-size: 16px; font-weight: 600; color: #ffffff; text-decoration: none;">View Your Group</a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 20px 30px; border-top: 1px solid #eeeeee;">
                            <p style="margin: 0; font-size: 14px; color: #666666; text-align: center;">Best regards,<br>{self._team_name}</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""

        text_content = f"""New Group Message

Hi {name},

{sender_name} left a message in {group_name}:

"{message_preview}"

View Your Group: {circles_link}

Best regards,
{self._team_name}
"""

        return await self._send(
            to=to_email,
            subject=f"{sender_name} left a message in {group_name}",
            html=html_content,
            text=text_content,
        )

    async def send_group_message_emails_batch(
        self,
        recipients: list,
        sender_name: str = "",
        group_name: str = "",
        message_preview: str = "",
    ) -> dict:
        """
        Send group message notification emails in a single batch.

        Args:
            recipients: List of dicts with 'email' and optional 'name' keys
            sender_name: Name of the message sender
            group_name: Name of the group
            message_preview: First 100 chars of the message

        Returns:
            dict with success status and results
        """
        if not recipients:
            return {"success": True, "data": []}

        circles_link = f"{self._app_url}/circles"
        subject = f"{sender_name} left a message in {group_name}"

        emails = []
        for recipient in recipients:
            name = recipient.get("name") or "there"
            to_email = recipient["email"]

            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; background-color: #f5f5f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; line-height: 1.6; color: #333333;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color: #f5f5f5;">
        <tr>
            <td align="center" style="padding: 20px 0;">
                <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; max-width: 600px;">
                    <tr>
                        <td align="center" bgcolor="#2D4A47" style="background-color: #2D4A47; padding: 40px 20px;">
                            <h1 style="margin: 0; font-size: 28px; color: #ffffff; font-weight: 600;">New Group Message</h1>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 40px 30px;">
                            <p style="margin: 0 0 16px 0; font-size: 16px; color: #333333;">Hi {name},</p>
                            <p style="margin: 0 0 24px 0; font-size: 16px; color: #333333;"><strong>{sender_name}</strong> left a message in <strong>{group_name}</strong>:</p>
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin: 20px 0;">
                                <tr>
                                    <td bgcolor="#f5f5f5" style="background-color: #f5f5f5; padding: 20px; border-radius: 8px; border-left: 4px solid #2D4A47;">
                                        <p style="margin: 0; font-size: 15px; color: #333333; font-style: italic;">"{message_preview}"</p>
                                    </td>
                                </tr>
                            </table>
                            <table role="presentation" cellpadding="0" cellspacing="0" style="margin: 24px auto;">
                                <tr>
                                    <td align="center" bgcolor="#2D4A47" style="background-color: #2D4A47; border-radius: 8px;">
                                        <a href="{circles_link}" target="_blank" style="display: inline-block; padding: 14px 28px; font-size: 16px; font-weight: 600; color: #ffffff; text-decoration: none;">View Your Group</a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 20px 30px; border-top: 1px solid #eeeeee;">
                            <p style="margin: 0; font-size: 14px; color: #666666; text-align: center;">Best regards,<br>{self._team_name}</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""

            text_content = f"""New Group Message

Hi {name},

{sender_name} left a message in {group_name}:

"{message_preview}"

View Your Group: {circles_link}

Best regards,
{self._team_name}
"""

            emails.append({
                "to": to_email,
                "subject": subject,
                "html": html_content,
                "text": text_content,
            })

        # Send in chunks of EMAIL_MAX_BATCH_SIZE
        results = []
        for i in range(0, len(emails), EMAIL_MAX_BATCH_SIZE):
            chunk = emails[i:i + EMAIL_MAX_BATCH_SIZE]
            result = await self._send_resend_batch(chunk)
            results.append(result)

        failed = [r for r in results if not r.get("success")]
        if failed:
            logger.warning(f"Some batch emails failed: {len(failed)}/{len(results)} batches")

        return {
            "success": len(failed) == 0,
            "batches": len(results),
            "total_emails": len(emails),
        }

    async def send_meeting_scheduled_email(
        self,
        to_email: str,
        user_name: Optional[str] = None,
        discussion_title: str = "",
        meeting_datetime: str = "",
        timezone: str = "UTC",
        meeting_link: str = "",
        language: str = "en",
    ) -> dict:
        """
        Send meeting scheduled notification email.

        Args:
            to_email: Recipient email address
            user_name: User's first name (optional)
            discussion_title: Title/topic of the meeting
            meeting_datetime: Formatted date and time string
            timezone: Timezone string
            meeting_link: URL to join the meeting
            language: Language code ("en" or "sv")

        Returns:
            dict with success status and message
        """
        name = user_name or "there"

        # Get translations
        t = self._get_translations(language, "meeting_scheduled", {
            "name": name,
            "title": discussion_title
        })

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <!--[if mso]>
    <style type="text/css">
        body, table, td {{font-family: Arial, Helvetica, sans-serif !important;}}
    </style>
    <![endif]-->
</head>
<body style="margin: 0; padding: 0; background-color: #f5f5f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; line-height: 1.6; color: #333333;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color: #f5f5f5;">
        <tr>
            <td align="center" style="padding: 20px 0;">
                <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; max-width: 600px;">
                    <!-- Header -->
                    <tr>
                        <td align="center" bgcolor="#2D4A47" style="background-color: #2D4A47; padding: 40px 20px;">
                            <h1 style="margin: 0; font-size: 28px; color: #ffffff; font-weight: 600;">{t.get("header", "Meeting Scheduled")}</h1>
                        </td>
                    </tr>
                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px 30px;">
                            <p style="margin: 0 0 16px 0; font-size: 16px; color: #333333;">{t.get("greeting", f"Hi {name},")}</p>
                            <p style="margin: 0 0 24px 0; font-size: 16px; color: #333333;">{t.get("body", "A new Think Tank meeting has been scheduled for your group.")}</p>

                            <!-- Info Box -->
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin: 20px 0;">
                                <tr>
                                    <td bgcolor="#f5f5f5" style="background-color: #f5f5f5; padding: 20px; border-radius: 8px;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                                            <tr>
                                                <td style="padding: 0 0 12px 0;">
                                                    <p style="margin: 0 0 4px 0; font-size: 14px; color: #666666;">{t.get("topic_label", "Discussion Topic")}</p>
                                                    <p style="margin: 0; font-size: 16px; font-weight: 600; color: #333333;">{discussion_title}</p>
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 12px 0 0 0;">
                                                    <p style="margin: 0 0 4px 0; font-size: 14px; color: #666666;">{t.get("when_label", "When")}</p>
                                                    <p style="margin: 0; font-size: 16px; font-weight: 600; color: #333333;">{meeting_datetime} ({timezone})</p>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>

                            <!-- Button -->
                            <table role="presentation" cellpadding="0" cellspacing="0" style="margin: 24px auto;">
                                <tr>
                                    <td align="center" bgcolor="#2D4A47" style="background-color: #2D4A47; border-radius: 8px;">
                                        <a href="{meeting_link}" target="_blank" style="display: inline-block; padding: 14px 28px; font-size: 16px; font-weight: 600; color: #ffffff; text-decoration: none;">{t.get("button", "Join Meeting")}</a>
                                    </td>
                                </tr>
                            </table>

                            <p style="margin: 0; font-size: 16px; color: #333333;">{t.get("closing", "We look forward to seeing you there.")}</p>
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 20px 30px; border-top: 1px solid #eeeeee;">
                            <p style="margin: 0; font-size: 14px; color: #666666; text-align: center;">{t.get("sign_off", "Best,")}<br>{self._team_name}</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""

        text_content = f"""
{t.get("subject", f"Human First AI Meeting Scheduled: {discussion_title}")}

{t.get("greeting", f"Hi {name},")}

{t.get("body", "A new Think Tank meeting has been scheduled for your group.")}

{t.get("topic_label", "Discussion Topic")}: {discussion_title}

{t.get("when_label", "When")}: {meeting_datetime} ({timezone})

{t.get("button", "Join Meeting")}: {meeting_link}

{t.get("closing", "We look forward to seeing you there.")}

{t.get("sign_off", "Best,")}
{self._team_name}
"""

        return await self._send(
            to=to_email,
            subject=t.get("subject", f"Human First AI Meeting Scheduled: {discussion_title}"),
            html=html_content,
            text=text_content,
        )

    async def send_password_reset_email(
        self,
        to_email: str,
        reset_link: str,
        user_name: Optional[str] = None,
        language: str = "en",
    ) -> dict:
        """
        Send password reset email.

        Args:
            to_email: Recipient email address
            reset_link: Firebase password reset link
            user_name: User's display name (optional)
            language: Language code ("en" or "sv")

        Returns:
            dict with success status and message
        """
        name = user_name or "there"

        # Get translations
        t = self._get_translations(language, "password_reset", {"name": name})

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <!--[if mso]>
    <style type="text/css">
        body, table, td {{font-family: Arial, Helvetica, sans-serif !important;}}
    </style>
    <![endif]-->
</head>
<body style="margin: 0; padding: 0; background-color: #f5f5f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; line-height: 1.6; color: #333333;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color: #f5f5f5;">
        <tr>
            <td align="center" style="padding: 20px 0;">
                <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; max-width: 600px;">
                    <!-- Header -->
                    <tr>
                        <td align="center" bgcolor="#2D4A47" style="background-color: #2D4A47; padding: 40px 20px;">
                            <h1 style="margin: 0; font-size: 28px; color: #ffffff; font-weight: 600;">{t.get("header", "Reset your password")}</h1>
                        </td>
                    </tr>
                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px 30px;">
                            <p style="margin: 0 0 16px 0; font-size: 16px; color: #333333;">{t.get("greeting", f"Hi {name},")}</p>
                            <p style="margin: 0 0 24px 0; font-size: 16px; color: #333333;">{t.get("body", "We received a request to reset your password. Click the button below to create a new password:")}</p>

                            <!-- Button -->
                            <table role="presentation" cellpadding="0" cellspacing="0" style="margin: 24px auto;">
                                <tr>
                                    <td align="center" bgcolor="#2D4A47" style="background-color: #2D4A47; border-radius: 8px;">
                                        <a href="{reset_link}" target="_blank" style="display: inline-block; padding: 14px 28px; font-size: 16px; font-weight: 600; color: #ffffff; text-decoration: none;">{t.get("button", "Reset Password")}</a>
                                    </td>
                                </tr>
                            </table>

                            <p style="margin: 24px 0 8px 0; font-size: 14px; color: #666666;">{t.get("link_fallback", "Or copy and paste this link into your browser:")}</p>
                            <p style="margin: 0 0 24px 0; font-size: 14px; color: #2D4A47; word-break: break-all;">{reset_link}</p>
                            <p style="margin: 0; font-size: 16px; color: #333333;">{t.get("ignore_notice", "If you didn't request a password reset, you can safely ignore this email.")}</p>
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 20px 30px; border-top: 1px solid #eeeeee;">
                            <p style="margin: 0; font-size: 14px; color: #666666; text-align: center;">{t.get("sign_off", "Best regards,")}<br>{self._team_name}</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""

        text_content = f"""
{t.get("header", "Reset your password")}

{t.get("greeting", f"Hi {name},")}

{t.get("body", "We received a request to reset your password. Click the link below to create a new password:")}

{reset_link}

{t.get("ignore_notice", "If you didn't request a password reset, you can safely ignore this email.")}

{t.get("sign_off", "Best regards,")}
{self._team_name}
"""

        return await self._send(
            to=to_email,
            subject=t.get("subject", "Reset your password"),
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
                    RESEND_API_URL,
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

    async def _send_resend_batch(self, emails: list) -> dict:
        """
        Send multiple emails via Resend Batch API.

        Args:
            emails: List of email dicts with keys: to, subject, html, text

        Returns:
            dict with success status and results
        """
        if not self._resend_api_key:
            return {"success": False, "error": "Resend API key not configured"}

        if not emails:
            return {"success": True, "data": []}

        # Limit batch size
        if len(emails) > EMAIL_MAX_BATCH_SIZE:
            emails = emails[:EMAIL_MAX_BATCH_SIZE]
            logger.warning(f"Batch size exceeded {EMAIL_MAX_BATCH_SIZE}, truncating")

        # Build batch payload
        batch_payload = []
        for email in emails:
            batch_payload.append({
                "from": f"{self._from_name} <{self._from_email}>",
                "to": [email["to"]],
                "subject": email["subject"],
                "html": email["html"],
                "text": email["text"],
            })

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    RESEND_BATCH_API_URL,
                    headers={
                        "Authorization": f"Bearer {self._resend_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=batch_payload,
                    timeout=30.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Batch email sent: {len(emails)} emails")
                    return {
                        "success": True,
                        "mode": "resend_batch",
                        "data": data.get("data", []),
                        "count": len(emails),
                    }
                else:
                    error_data = response.json()
                    error_msg = error_data.get("message", "Unknown error")
                    logger.error(f"Resend Batch API error: {error_msg}")
                    return {
                        "success": False,
                        "error": error_msg,
                    }

            except Exception as e:
                logger.error(f"Failed to send batch email via Resend: {e}")
                return {
                    "success": False,
                    "error": str(e),
                }

    async def send_circle_invitation_emails_batch(
        self,
        invitations: list,
        pool_name: str,
        topic: str = None,
        custom_message: str = None,
    ) -> dict:
        """
        Send circle invitation emails in batch.

        Args:
            invitations: List of dicts with keys: email, token, firstName, language, expires_at
            pool_name: Name of the circle pool
            topic: Discussion topic (optional)
            custom_message: Custom message from inviter (optional)

        Returns:
            dict with success status and count
        """
        if self._mode == "console":
            for inv in invitations[:EMAIL_MAX_BATCH_SIZE]:
                logger.info(f"[BATCH] Would send invitation to {inv['email']}")
            return {"success": True, "mode": "console", "count": len(invitations)}

        emails = []
        for inv in invitations[:EMAIL_MAX_BATCH_SIZE]:
            email = inv.get("email")
            token = inv.get("token")
            first_name = inv.get("firstName") or "there"
            language = inv.get("language", "en")
            expires_at = inv.get("expires_at", "")

            # Get translations
            t = self._get_translations(language, "circle_invitation", {
                "name": first_name,
                "pool_name": pool_name,
                "expires_at": expires_at
            })

            accept_link = f"{self._api_url}/api/circles/invitations/{token}/accept"
            decline_link = f"{self._api_url}/api/circles/invitations/{token}/decline"

            # Build topic section
            topic_html = ""
            if topic:
                topic_label = t.get("topic_label", "Topic:")
                topic_html = f'<p style="margin: 16px 0 0 0; font-size: 16px; color: #666666;"><strong>{topic_label}</strong> {topic}</p>'

            # Build custom message section
            message_html = ""
            if custom_message:
                message_html = f'''
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin: 20px 0;">
                                <tr>
                                    <td bgcolor="#f5f5f5" style="background-color: #f5f5f5; padding: 16px; border-radius: 8px;">
                                        <p style="margin: 0; font-size: 16px; font-style: italic; color: #333333;">"{custom_message}"</p>
                                    </td>
                                </tr>
                            </table>'''

            # Build expiry section
            expiry_html = ""
            if expires_at:
                expiry_notice = t.get("expiry_notice", f"This invitation expires on {expires_at}.")
                expiry_html = f'<p style="margin: 20px 0 0 0; font-size: 14px; color: #999999;">{expiry_notice}</p>'

            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <!--[if mso]>
    <style type="text/css">
        body, table, td {{font-family: Arial, Helvetica, sans-serif !important;}}
    </style>
    <![endif]-->
</head>
<body style="margin: 0; padding: 0; background-color: #f5f5f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; line-height: 1.6; color: #333333;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color: #f5f5f5;">
        <tr>
            <td align="center" style="padding: 20px 0;">
                <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; max-width: 600px;">
                    <!-- Header -->
                    <tr>
                        <td align="center" bgcolor="#2D4A47" style="background-color: #2D4A47; padding: 40px 20px;">
                            <h1 style="margin: 0; font-size: 28px; color: #ffffff; font-weight: 600;">{t.get("header", "You're Invited!")}</h1>
                        </td>
                    </tr>
                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px 30px;">
                            <p style="margin: 0 0 16px 0; font-size: 16px; color: #333333;">{t.get("greeting", f"Hi {first_name},")}</p>
                            <p style="margin: 0 0 16px 0; font-size: 16px; color: #333333;">{t.get("body", f"You've been invited to join <strong>{pool_name}</strong>, where you'll connect with peers for meaningful conversations and mutual support.")}</p>
                            {topic_html}
                            {message_html}

                            <!-- Buttons -->
                            <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="margin: 30px 0;">
                                <tr>
                                    <td align="center">
                                        <table role="presentation" cellpadding="0" cellspacing="0">
                                            <tr>
                                                <td align="center" bgcolor="#2D4A47" style="background-color: #2D4A47; border-radius: 8px;">
                                                    <a href="{accept_link}" target="_blank" style="display: inline-block; padding: 14px 28px; font-size: 16px; font-weight: 600; color: #ffffff; text-decoration: none;">{t.get("accept_button", "Accept Invitation")}</a>
                                                </td>
                                                <td width="20"></td>
                                                <td align="center" bgcolor="#e5e7eb" style="background-color: #e5e7eb; border-radius: 8px;">
                                                    <a href="{decline_link}" target="_blank" style="display: inline-block; padding: 14px 28px; font-size: 16px; font-weight: 600; color: #374151; text-decoration: none;">{t.get("decline_button", "Decline")}</a>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>

                            <p style="margin: 24px 0 8px 0; font-size: 14px; color: #666666;">{t.get("link_fallback", "Or copy and paste this link into your browser:")}</p>
                            <p style="margin: 0 0 16px 0; font-size: 14px; color: #2D4A47; word-break: break-all;">{accept_link}</p>
                            {expiry_html}
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 20px 30px; border-top: 1px solid #eeeeee;">
                            <p style="margin: 0; font-size: 14px; color: #666666; text-align: center;">{t.get("sign_off", "Best regards,")}<br>{self._team_name}</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""

            text_content = f"""
{t.get("header", "You're Invited!")}

{t.get("greeting", f"Hi {first_name},")}

{t.get("body", f"You've been invited to join {pool_name}, where you'll connect with peers for meaningful conversations and mutual support.")}

{t.get("accept_button", "Accept Invitation")}: {accept_link}

{t.get("decline_button", "Decline")}: {decline_link}

{t.get("sign_off", "Best regards,")}
{self._team_name}
"""

            emails.append({
                "to": email,
                "subject": t.get("subject", f"You're invited to join {pool_name}"),
                "html": html_content,
                "text": text_content,
            })

        return await self._send_resend_batch(emails)
