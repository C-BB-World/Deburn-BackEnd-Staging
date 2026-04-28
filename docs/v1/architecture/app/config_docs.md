# Settings

BrainBank application settings. Extends BaseAppSettings with app-specific configuration.

---

## Classes

### Settings

BrainBank-specific settings. Extends BaseAppSettings.

**Properties:**

Secondary Database (Hub):
- `HUB_MONGODB_URI` (Optional[str]): Hub MongoDB URI. Falls back to main URI if not set.
- `HUB_MONGODB_DATABASE` (str): Hub database name. Default: "brainbank_hub"

External Services:
- `ELEVENLABS_API_KEY` (Optional[str]): ElevenLabs TTS API key
- `ELEVENLABS_VOICE_ID` (str): Default voice ID. Default: "EXAVITQu4vr4xnSDxMaL"
- `FAL_API_KEY` (Optional[str]): FAL.ai image generation API key

Application Settings:
- `DAILY_EXCHANGE_LIMIT` (int): Daily coach exchange limit per user. Default: 15
- `SESSION_EXPIRE_DAYS` (int): Session expiration days. Default: 30
- `PASSWORD_RESET_EXPIRE_HOURS` (int): Password reset expiration. Default: 24
- `EMAIL_VERIFICATION_EXPIRE_HOURS` (int): Email verification expiration. Default: 48
- `DELETION_GRACE_PERIOD_DAYS` (int): Account deletion grace period (GDPR). Default: 30

Circle Settings:
- `DEFAULT_MEETING_DURATION` (int): Default meeting duration in minutes. Default: 60
- `DEFAULT_GROUP_SIZE` (int): Default group size for circles. Default: 4

Email Settings:
- `SMTP_HOST` (Optional[str]): SMTP server host
- `SMTP_PORT` (int): SMTP port. Default: 587
- `SMTP_USER` (Optional[str]): SMTP username
- `SMTP_PASSWORD` (Optional[str]): SMTP password
- `SMTP_FROM_EMAIL` (str): From email. Default: "noreply@brainbank.ai"
- `SMTP_FROM_NAME` (str): From name. Default: "BrainBank"

Frontend URL:
- `FRONTEND_URL` (str): Frontend URL for email links. Default: "http://localhost:3000"

**Methods:**

#### get_hub_uri

- **Inputs:** None
- **Outputs:** (str) Hub MongoDB URI
- **Description:** Get Hub MongoDB URI, falling back to main URI if not set.

---

## Module Variables

### settings

- **Type:** Settings
- **Description:** Global settings instance
