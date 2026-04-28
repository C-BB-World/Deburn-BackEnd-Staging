"""
Public routes — no authentication required.

Endpoints for the landing page: testimonials and contact form.
"""

import logging
import os
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, EmailStr, Field

from common.utils import success_response
from app_v2.dependencies import get_feedback_service, get_hub_db
from app_v2.services.email.email_service import EmailService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/public")

# ---------------------------------------------------------------------------
# Simple in-memory rate limiter (5 requests per hour per IP)
# ---------------------------------------------------------------------------
_contact_rate: dict = defaultdict(list)
CONTACT_RATE_LIMIT = 5
CONTACT_RATE_WINDOW = 3600  # 1 hour in seconds


def _check_rate_limit(ip: str) -> bool:
    """Return True if the request is allowed, False if rate-limited."""
    now = time.time()
    # Prune old entries
    _contact_rate[ip] = [t for t in _contact_rate[ip] if now - t < CONTACT_RATE_WINDOW]
    if len(_contact_rate[ip]) >= CONTACT_RATE_LIMIT:
        return False
    _contact_rate[ip].append(now)
    return True


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class ContactRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    company: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    message: str = Field("", max_length=3000)


# ---------------------------------------------------------------------------
# GET /public/testimonials?lang=en|sv
# ---------------------------------------------------------------------------
@router.get("/testimonials")
async def get_testimonials(lang: str = Query("en", pattern="^(en|sv)$")):
    """Fetch featured testimonials for the landing page."""
    try:
        feedback_service = get_feedback_service()
        items = await feedback_service.get_featured_testimonials()

        data = []
        for f in items:
            content = f.get("content", "")
            if lang == "sv" and f.get("contentSv"):
                content = f["contentSv"]
            data.append({
                "content": content,
                "attribution": f.get("anonymousAttribution") or "Beta tester",
            })

        return success_response(data=data)
    except RuntimeError:
        # Service not initialized (hub_db unavailable)
        return success_response(data=[])
    except Exception as e:
        logger.error(f"Error fetching testimonials: {e}")
        return success_response(data=[])


# ---------------------------------------------------------------------------
# POST /public/contact
# ---------------------------------------------------------------------------
@router.post("/contact")
async def submit_contact(body: ContactRequest, request: Request):
    """Submit a demo request from the landing page."""
    client_ip = request.client.host if request.client else "unknown"

    if not _check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Too many contact requests. Please try again in an hour.",
        )

    clean_name = body.name.strip()
    clean_company = body.company.strip()
    clean_email = body.email.lower().strip()
    clean_message = body.message.strip() if body.message else ""

    try:
        hub_db = get_hub_db()
        await hub_db["contact_submissions"].insert_one({
            "name": clean_name,
            "company": clean_company,
            "email": clean_email,
            "message": clean_message,
            "createdAt": datetime.now(timezone.utc),
            "ip": client_ip,
        })
    except Exception as e:
        logger.error(f"Failed to store contact submission: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit request. Please try again.")

    # Send notification email (non-blocking — don't fail the request)
    try:
        email_service = EmailService()
        subject = f"Demo request from {clean_name} at {clean_company}"
        text = (
            f"New demo request\n\n"
            f"Name: {clean_name}\n"
            f"Company: {clean_company}\n"
            f"Email: {clean_email}\n\n"
            f"Message:\n{clean_message}"
        )
        html = (
            f"<h2>New Demo Request</h2>"
            f"<p><strong>Name:</strong> {clean_name}</p>"
            f"<p><strong>Company:</strong> {clean_company}</p>"
            f"<p><strong>Email:</strong> <a href='mailto:{clean_email}'>{clean_email}</a></p>"
            f"<hr><p>{clean_message.replace(chr(10), '<br>')}</p>"
        )
        await email_service._send(
            to=os.environ.get("CONTACT_NOTIFICATION_EMAIL", "hfai@brainbank.world"),
            subject=subject,
            html=html,
            text=text,
        )
    except Exception as e:
        logger.warning(f"Failed to send contact notification email: {e}")

    return success_response()
