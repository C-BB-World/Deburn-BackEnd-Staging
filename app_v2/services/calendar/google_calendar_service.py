"""
Google Calendar API client.

Manages OAuth, calendar operations, and webhook setup.
"""

import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

import httpx

logger = logging.getLogger(__name__)


class GoogleCalendarService:
    """
    Google Calendar API client.
    Manages OAuth, calendar operations, and webhook setup.
    """

    OAUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    REVOKE_URL = "https://oauth2.googleapis.com/revoke"
    USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
    CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"

    SCOPES = [
        "https://www.googleapis.com/auth/calendar.readonly",
        "https://www.googleapis.com/auth/calendar.events",
        "https://www.googleapis.com/auth/userinfo.email",
    ]

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        webhook_url: Optional[str] = None
    ):
        """
        Initialize GoogleCalendarService.

        Args:
            client_id: Google OAuth client ID
            client_secret: Google OAuth client secret
            redirect_uri: OAuth callback URL
            webhook_url: URL for calendar webhooks
        """
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._webhook_url = webhook_url

    def get_auth_url(self, state: Optional[str] = None) -> str:
        """
        Generate Google OAuth authorization URL.

        Args:
            state: Opaque state value (user ID, return URL)

        Returns:
            Authorization URL to redirect user to
        """
        params = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.SCOPES),
            "access_type": "offline",
            "prompt": "consent",
        }

        if state:
            params["state"] = state

        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.OAUTH_URL}?{query}"

    async def exchange_code(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for tokens.

        Args:
            code: Authorization code from OAuth callback

        Returns:
            dict with access_token, refresh_token, expires_in
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "code": code,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "redirect_uri": self._redirect_uri,
                    "grant_type": "authorization_code",
                }
            )

            if response.status_code != 200:
                logger.error(f"Token exchange failed: {response.text}")
                raise ValueError(f"Token exchange failed: {response.status_code}")

            data = response.json()
            return {
                "accessToken": data["access_token"],
                "refreshToken": data.get("refresh_token"),
                "expiresIn": data["expires_in"],
                "tokenType": data["token_type"],
            }

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh an expired access token.

        Args:
            refresh_token: Refresh token from initial auth

        Returns:
            dict with new access_token, expires_in
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "refresh_token": refresh_token,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "grant_type": "refresh_token",
                }
            )

            if response.status_code != 200:
                logger.error(f"Token refresh failed: {response.text}")
                raise ValueError(f"Token refresh failed: {response.status_code}")

            data = response.json()
            return {
                "accessToken": data["access_token"],
                "expiresIn": data["expires_in"],
            }

    async def revoke_token(self, access_token: str) -> bool:
        """
        Revoke OAuth tokens with Google.

        Args:
            access_token: Token to revoke

        Returns:
            True if revoked successfully
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.REVOKE_URL,
                params={"token": access_token}
            )
            return response.status_code == 200

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Get user email from Google.

        Args:
            access_token: Valid access token

        Returns:
            dict with email, name
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"}
            )

            if response.status_code != 200:
                logger.error(f"User info fetch failed: {response.text}")
                raise ValueError("Failed to get user info")

            return response.json()

    async def list_calendars(self, access_token: str) -> List[Dict[str, Any]]:
        """
        List user's calendars.

        Args:
            access_token: Valid access token

        Returns:
            List of calendars: [{ id, summary, primary }]
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.CALENDAR_API_BASE}/users/me/calendarList",
                headers={"Authorization": f"Bearer {access_token}"}
            )

            if response.status_code != 200:
                logger.error(f"List calendars failed: {response.text}")
                return []

            data = response.json()
            return [
                {
                    "id": cal["id"],
                    "summary": cal.get("summary", ""),
                    "primary": cal.get("primary", False),
                }
                for cal in data.get("items", [])
            ]

    async def get_free_busy(
        self,
        access_token: str,
        calendar_ids: List[str],
        time_min: datetime,
        time_max: datetime
    ) -> List[Dict[str, Any]]:
        """
        Query free/busy for calendars.

        Args:
            access_token: Valid access token
            calendar_ids: List of calendar IDs to check
            time_min: Start of range
            time_max: End of range

        Returns:
            List of busy slots: [{ start, end, calendarId }]
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.CALENDAR_API_BASE}/freeBusy",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "timeMin": time_min.isoformat(),
                    "timeMax": time_max.isoformat(),
                    "items": [{"id": cal_id} for cal_id in calendar_ids],
                }
            )

            if response.status_code != 200:
                logger.error(f"Free/busy query failed: {response.text}")
                return []

            data = response.json()
            busy_slots = []

            for cal_id, cal_data in data.get("calendars", {}).items():
                for busy in cal_data.get("busy", []):
                    busy_slots.append({
                        "start": datetime.fromisoformat(busy["start"].replace("Z", "+00:00")),
                        "end": datetime.fromisoformat(busy["end"].replace("Z", "+00:00")),
                        "calendarId": cal_id,
                    })

            return busy_slots

    async def create_event(
        self,
        access_token: str,
        calendar_id: str,
        event: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a calendar event.

        Args:
            access_token: Valid access token
            calendar_id: Calendar to create event in
            event: Event details (summary, start, end, attendees, etc.)

        Returns:
            Created event with id, htmlLink, meetLink
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.CALENDAR_API_BASE}/calendars/{calendar_id}/events",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                params={"conferenceDataVersion": 1},
                json=event
            )

            if response.status_code not in (200, 201):
                logger.error(f"Create event failed: {response.text}")
                raise ValueError(f"Failed to create event: {response.status_code}")

            data = response.json()
            meet_link = None
            if "conferenceData" in data:
                entry_points = data["conferenceData"].get("entryPoints", [])
                for ep in entry_points:
                    if ep.get("entryPointType") == "video":
                        meet_link = ep.get("uri")
                        break

            return {
                "id": data["id"],
                "htmlLink": data.get("htmlLink"),
                "meetLink": meet_link,
            }

    async def update_event(
        self,
        access_token: str,
        calendar_id: str,
        event_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update an existing event.

        Args:
            access_token: Valid access token
            calendar_id: Calendar containing event
            event_id: Event to update
            updates: Fields to update

        Returns:
            Updated event
        """
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.CALENDAR_API_BASE}/calendars/{calendar_id}/events/{event_id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=updates
            )

            if response.status_code != 200:
                logger.error(f"Update event failed: {response.text}")
                raise ValueError(f"Failed to update event: {response.status_code}")

            return response.json()

    async def delete_event(
        self,
        access_token: str,
        calendar_id: str,
        event_id: str,
        send_updates: bool = True
    ) -> bool:
        """
        Delete a calendar event.

        Args:
            access_token: Valid access token
            calendar_id: Calendar containing event
            event_id: Event to delete
            send_updates: Send cancellation to attendees

        Returns:
            True if deleted
        """
        async with httpx.AsyncClient() as client:
            params = {}
            if send_updates:
                params["sendUpdates"] = "all"

            response = await client.delete(
                f"{self.CALENDAR_API_BASE}/calendars/{calendar_id}/events/{event_id}",
                headers={"Authorization": f"Bearer {access_token}"},
                params=params
            )

            return response.status_code in (200, 204)

    async def setup_webhook(
        self,
        access_token: str,
        calendar_id: str,
        channel_id: str,
        token: str,
        expiration: datetime
    ) -> Dict[str, Any]:
        """
        Setup push notification webhook for calendar.

        Args:
            access_token: Valid access token
            calendar_id: Calendar to watch
            channel_id: Unique channel identifier
            token: Verification token for webhook
            expiration: When webhook expires

        Returns:
            dict with resourceId, expiration
        """
        if not self._webhook_url:
            raise ValueError("Webhook URL not configured")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.CALENDAR_API_BASE}/calendars/{calendar_id}/events/watch",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "id": channel_id,
                    "type": "web_hook",
                    "address": self._webhook_url,
                    "token": token,
                    "expiration": int(expiration.timestamp() * 1000),
                }
            )

            if response.status_code != 200:
                logger.error(f"Webhook setup failed: {response.text}")
                raise ValueError(f"Failed to setup webhook: {response.status_code}")

            data = response.json()
            return {
                "resourceId": data["resourceId"],
                "expiration": datetime.fromtimestamp(
                    int(data["expiration"]) / 1000,
                    tz=timezone.utc
                ),
            }

    async def stop_webhook(
        self,
        channel_id: str,
        resource_id: str
    ) -> bool:
        """
        Stop a webhook channel.

        Args:
            channel_id: Channel to stop
            resource_id: Resource ID from setup

        Returns:
            True if stopped
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.CALENDAR_API_BASE}/channels/stop",
                headers={"Content-Type": "application/json"},
                json={
                    "id": channel_id,
                    "resourceId": resource_id,
                }
            )

            return response.status_code in (200, 204)

    async def sync_events(
        self,
        access_token: str,
        calendar_id: str,
        sync_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sync calendar events (full or incremental).

        Args:
            access_token: Valid access token
            calendar_id: Calendar to sync
            sync_token: Token for incremental sync (None for full)

        Returns:
            dict with events list and nextSyncToken
        """
        async with httpx.AsyncClient() as client:
            params = {}
            if sync_token:
                params["syncToken"] = sync_token
            else:
                params["timeMin"] = datetime.now(timezone.utc).isoformat()

            response = await client.get(
                f"{self.CALENDAR_API_BASE}/calendars/{calendar_id}/events",
                headers={"Authorization": f"Bearer {access_token}"},
                params=params
            )

            if response.status_code == 410:
                return {"events": [], "nextSyncToken": None, "fullSyncRequired": True}

            if response.status_code != 200:
                logger.error(f"Sync events failed: {response.text}")
                raise ValueError(f"Failed to sync events: {response.status_code}")

            data = response.json()
            return {
                "events": data.get("items", []),
                "nextSyncToken": data.get("nextSyncToken"),
                "fullSyncRequired": False,
            }

    def generate_channel_id(self) -> str:
        """Generate a unique channel ID for webhooks."""
        return secrets.token_urlsafe(32)

    def generate_channel_token(self) -> str:
        """Generate a verification token for webhooks."""
        return secrets.token_urlsafe(32)
