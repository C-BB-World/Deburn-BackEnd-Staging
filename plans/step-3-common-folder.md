# Step 3: Create Common Folder

## Overview

Create a `common/` folder containing **generic, reusable infrastructure** that can be used across multiple projects. This will eventually become a standalone library. App-specific code (models, locales) goes in a separate `app/` folder.

## Objective

- Create generic infrastructure components (not BrainBank-specific)
- Follow SOLID principles for extensibility
- Design for reuse across different projects
- Keep app-specific code separate in `app/`

## Design Principles

1. **No hardcoded values** - Everything configurable via parameters or settings
2. **No app-specific models** - User, CheckIn, etc. belong in `app/`
3. **Interface-driven** - Abstract base classes for swappable implementations
4. **Minimal dependencies** - Each module should be independently usable

## Files to Reference

### Database Configuration
- `config/database.js` - Main MongoDB connection pattern
- `config/hubDatabase.js` - Secondary database connection pattern

### Authentication
- `middleware/auth.js` - JWT verification patterns
- `services/authService.js` - Auth logic
- `services/tokenService.js` - Token management

### Services (for patterns)
- `services/i18nService.js` - Internationalization pattern

### Utilities
- `utils/passwordValidator.js` - Password validation rules

## Output Structure

```
back-end/
  common/                      # GENERIC REUSABLE LIBRARY
    __init__.py
    database/
      __init__.py
      mongodb.py               # Generic async MongoDB connection
      base_document.py         # Base Beanie document class
    auth/
      __init__.py
      base.py                  # Abstract AuthProvider interface
      jwt_auth.py              # JWT + bcrypt implementation
      firebase_auth.py         # Firebase Admin SDK implementation
      dependencies.py          # Generic FastAPI auth dependencies
    ai/
      __init__.py
      base.py                  # Abstract AIProvider interface
      claude.py                # Anthropic Claude implementation
      openai.py                # OpenAI implementation (optional)
    i18n/
      __init__.py
      service.py               # Generic i18n service (configurable)
    utils/
      __init__.py
      responses.py             # Standard API response helpers
      exceptions.py            # Generic HTTP exceptions
      password.py              # Password strength validation
    config/
      __init__.py
      base_settings.py         # Base Pydantic Settings class

  app/                         # BRAINBANK-SPECIFIC
    __init__.py
    models/
      __init__.py
      user.py                  # User document
      checkin.py               # CheckIn document
      organization.py          # Organization document
      circle.py                # Circle-related documents
      coach.py                 # Coach/commitment documents
      content.py               # Content/learning documents
    services/
      __init__.py
      coach_service.py         # BrainBank coaching logic (uses common/ai)
    locales/
      en/                      # English translations
      sv/                      # Swedish translations
      emails/                  # Email templates
    config.py                  # BrainBank settings (extends base)
    constants.py               # App-specific constants (countries, etc.)
```

## Implementation Details

### 1. Database Module (`common/database/`)

Generic async MongoDB connection using Beanie ODM.

#### mongodb.py
```python
from beanie import init_beanie, Document
from motor.motor_asyncio import AsyncIOMotorClient
from typing import List, Type, Optional

class MongoDB:
    """Generic MongoDB connection manager - works with any database"""

    def __init__(self):
        self._client: Optional[AsyncIOMotorClient] = None
        self._initialized: bool = False

    async def connect(
        self,
        uri: str,
        database_name: str,
        document_models: List[Type[Document]]
    ) -> None:
        """Connect to MongoDB and initialize Beanie with provided models"""
        self._client = AsyncIOMotorClient(uri)
        await init_beanie(
            database=self._client[database_name],
            document_models=document_models
        )
        self._initialized = True

    async def disconnect(self) -> None:
        if self._client:
            self._client.close()
            self._initialized = False

    @property
    def is_connected(self) -> bool:
        return self._initialized

    @property
    def client(self) -> Optional[AsyncIOMotorClient]:
        return self._client
```

#### base_document.py
```python
from beanie import Document
from datetime import datetime
from pydantic import Field

class BaseDocument(Document):
    """Base document with common fields - extend for app-specific models"""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        use_state_management = True
```

### 2. Authentication Module (`common/auth/`)

Supports both JWT+bcrypt and Firebase - switchable via config.

#### base.py - Abstract interface
```python
from abc import ABC, abstractmethod
from typing import Optional, Any

class AuthProvider(ABC):
    """Abstract auth provider - implement for different auth strategies"""

    @abstractmethod
    async def create_user(self, email: str, password: str, **kwargs) -> str:
        """Create new user, returns user id"""

    @abstractmethod
    async def verify_credentials(self, email: str, password: str) -> dict:
        """Verify email/password, return user info"""

    @abstractmethod
    async def create_token(self, user_id: str, **claims) -> str:
        """Create auth token for user"""

    @abstractmethod
    async def verify_token(self, token: str) -> dict:
        """Verify token, return decoded claims"""

    @abstractmethod
    async def revoke_token(self, token: str) -> None:
        """Revoke/invalidate a token"""

    @abstractmethod
    async def send_password_reset(self, email: str) -> str:
        """Send password reset, return reset token"""

    @abstractmethod
    async def reset_password(self, token: str, new_password: str) -> None:
        """Reset password with token"""

    @abstractmethod
    async def send_verification_email(self, email: str) -> str:
        """Send email verification, return verification token"""

    @abstractmethod
    async def verify_email(self, token: str) -> None:
        """Verify email with token"""

    @abstractmethod
    async def delete_user(self, user_id: str) -> None:
        """Delete user account"""
```

#### jwt_auth.py
```python
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
from passlib.hash import bcrypt
from .base import AuthProvider

class JWTAuth(AuthProvider):
    """JWT + bcrypt authentication provider"""

    def __init__(
        self,
        secret: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        reset_token_expire_hours: int = 24
    ):
        self.secret = secret
        self.algorithm = algorithm
        self.access_token_expire = timedelta(minutes=access_token_expire_minutes)
        self.reset_token_expire = timedelta(hours=reset_token_expire_hours)
        self._revoked_tokens: set = set()  # In production, use Redis

    def hash_password(self, password: str) -> str:
        return bcrypt.hash(password)

    def verify_password(self, password: str, hashed: str) -> bool:
        return bcrypt.verify(password, hashed)

    async def create_token(self, user_id: str, **claims) -> str:
        expire = datetime.utcnow() + self.access_token_expire
        payload = {"sub": user_id, "exp": expire, **claims}
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    async def verify_token(self, token: str) -> dict:
        if token in self._revoked_tokens:
            raise ValueError("Token has been revoked")
        try:
            payload = jwt.decode(token, self.secret, algorithms=[self.algorithm])
            return payload
        except JWTError as e:
            raise ValueError(f"Invalid token: {e}")

    # ... other methods implemented
```

#### firebase_auth.py
```python
from typing import Optional
from .base import AuthProvider

class FirebaseAuth(AuthProvider):
    """Firebase Admin SDK authentication provider"""

    def __init__(self, credentials_path: str):
        import firebase_admin
        from firebase_admin import credentials

        cred = credentials.Certificate(credentials_path)
        firebase_admin.initialize_app(cred)
        self._auth = firebase_admin.auth

    # ... implements all AuthProvider methods using Firebase
```

#### dependencies.py
```python
from typing import Callable, Optional
from fastapi import Header, HTTPException, Depends
from .base import AuthProvider

def create_auth_dependency(get_auth: Callable[[], AuthProvider]):
    """Factory to create auth dependencies with custom auth provider"""

    async def get_current_user_id(
        authorization: str = Header(..., alias="Authorization")
    ) -> str:
        """Extract and verify user ID from token"""
        if not authorization.startswith("Bearer "):
            raise HTTPException(401, "Invalid authorization header")

        token = authorization.replace("Bearer ", "")
        auth = get_auth()

        try:
            payload = await auth.verify_token(token)
            return payload["sub"]
        except ValueError as e:
            raise HTTPException(401, str(e))

    return get_current_user_id
```

### 3. AI Module (`common/ai/`)

Generic AI provider interface - supports Claude, OpenAI, or any LLM.

#### base.py - Abstract interface
```python
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional, List, Dict, Any

class AIProvider(ABC):
    """Abstract AI provider - implement for different LLM services"""

    @abstractmethod
    async def chat(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7
    ) -> str:
        """Send message and get response"""

    @abstractmethod
    async def stream_chat(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """Stream response chunks"""

    @abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for text"""
```

#### claude.py - Anthropic Claude implementation
```python
from typing import AsyncGenerator, Optional, List, Dict
from anthropic import Anthropic
from .base import AIProvider

class ClaudeProvider(AIProvider):
    """Anthropic Claude AI provider"""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-5-20250929",
        max_retries: int = 3
    ):
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.max_retries = max_retries

    async def chat(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7
    ) -> str:
        messages = conversation_history or []
        messages.append({"role": "user", "content": message})

        params = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": messages
        }
        if system_prompt:
            params["system"] = system_prompt

        response = self.client.messages.create(**params)
        return response.content[0].text

    async def stream_chat(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        messages = conversation_history or []
        messages.append({"role": "user", "content": message})

        params = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": messages,
            "stream": True
        }
        if system_prompt:
            params["system"] = system_prompt

        stream = self.client.messages.create(**params)
        for chunk in stream:
            if chunk.type == "content_block_delta" and chunk.delta.text:
                yield chunk.delta.text

    async def generate_embedding(self, text: str) -> List[float]:
        # Claude doesn't have embeddings API - raise or use voyageai
        raise NotImplementedError("Claude doesn't support embeddings directly")
```

#### openai.py - OpenAI implementation (optional)
```python
from typing import AsyncGenerator, Optional, List, Dict
from openai import AsyncOpenAI
from .base import AIProvider

class OpenAIProvider(AIProvider):
    """OpenAI GPT provider"""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        embedding_model: str = "text-embedding-3-small"
    ):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.embedding_model = embedding_model

    async def chat(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.extend(conversation_history or [])
        messages.append({"role": "user", "content": message})

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        return response.choices[0].message.content

    async def stream_chat(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.extend(conversation_history or [])
        messages.append({"role": "user", "content": message})

        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def generate_embedding(self, text: str) -> List[float]:
        response = await self.client.embeddings.create(
            model=self.embedding_model,
            input=text
        )
        return response.data[0].embedding
```

#### Usage - switch via config
```python
from common.ai.base import AIProvider
from common.ai.claude import ClaudeProvider
from common.ai.openai import OpenAIProvider

def get_ai_provider(settings) -> AIProvider:
    if settings.AI_PROVIDER == "openai":
        return OpenAIProvider(api_key=settings.OPENAI_API_KEY)
    else:  # default to claude
        return ClaudeProvider(api_key=settings.CLAUDE_API_KEY)
```

### 4. Internationalization Module (`common/i18n/`)

Generic i18n service - works with any languages/locales.

#### service.py
```python
import json
from pathlib import Path
from typing import Dict, List, Optional, Any

class I18nService:
    """Generic internationalization service - configurable for any languages"""

    def __init__(
        self,
        locales_dir: str,
        default_language: str = "en",
        supported_languages: Optional[List[str]] = None
    ):
        self.locales_dir = Path(locales_dir)
        self.default_language = default_language
        self.translations: Dict[str, Dict[str, Any]] = {}

        # Auto-detect supported languages from directory structure
        if supported_languages:
            self.supported_languages = supported_languages
        else:
            self.supported_languages = self._detect_languages()

        self._load_translations()

    def _detect_languages(self) -> List[str]:
        """Detect available languages from locale directory"""
        if not self.locales_dir.exists():
            return [self.default_language]
        return [d.name for d in self.locales_dir.iterdir() if d.is_dir()]

    def _load_translations(self) -> None:
        """Load all translation files at startup"""
        for lang in self.supported_languages:
            self.translations[lang] = {}
            lang_dir = self.locales_dir / lang

            if not lang_dir.exists():
                continue

            for file in lang_dir.glob("*.json"):
                namespace = file.stem
                try:
                    with open(file, "r", encoding="utf-8") as f:
                        self.translations[lang][namespace] = json.load(f)
                except (json.JSONDecodeError, IOError) as e:
                    print(f"Warning: Failed to load {file}: {e}")

    def _get_nested(self, data: dict, path: List[str]) -> Optional[Any]:
        """Get nested value using path list"""
        for key in path:
            if not isinstance(data, dict):
                return None
            data = data.get(key)
            if data is None:
                return None
        return data

    def t(
        self,
        key: str,
        language: Optional[str] = None,
        **options
    ) -> str:
        """
        Get translation by dot-notation key.

        Args:
            key: Dot notation key (e.g., 'auth.login.success')
            language: Language code (falls back to default)
            **options: Interpolation values and 'count' for pluralization

        Returns:
            Translated string or key if not found
        """
        lang = language if language in self.supported_languages else self.default_language
        parts = key.split(".")

        if len(parts) < 2:
            return key

        namespace = parts[0]
        path = parts[1:]

        # Try requested language
        value = self._get_nested(
            self.translations.get(lang, {}).get(namespace, {}),
            path
        )

        # Fallback to default language
        if value is None and lang != self.default_language:
            value = self._get_nested(
                self.translations.get(self.default_language, {}).get(namespace, {}),
                path
            )

        if value is None:
            return key

        # Handle pluralization
        if isinstance(value, dict) and "count" in options:
            count = options["count"]
            value = value.get("one" if count == 1 else "other", key)

        # Handle interpolation
        if isinstance(value, str):
            for var_name, var_value in options.items():
                value = value.replace(f"{{{{{var_name}}}}}", str(var_value))

        return value

    def is_supported(self, language: str) -> bool:
        return language in self.supported_languages
```

### 4. Utilities Module (`common/utils/`)

#### responses.py
```python
from typing import Any, Optional

def success_response(data: Any = None, message: Optional[str] = None) -> dict:
    """Standard success response format"""
    response = {"success": True}
    if data is not None:
        response["data"] = data
    if message:
        response["message"] = message
    return response

def error_response(
    message: str,
    code: Optional[str] = None,
    details: Optional[Any] = None
) -> dict:
    """Standard error response format"""
    error = {"message": message}
    if code:
        error["code"] = code
    if details:
        error["details"] = details
    return {"success": False, "error": error}
```

#### exceptions.py
```python
from fastapi import HTTPException
from typing import Optional

class APIException(HTTPException):
    """Base API exception with code support"""

    def __init__(
        self,
        status_code: int,
        message: str,
        code: Optional[str] = None
    ):
        detail = {"message": message}
        if code:
            detail["code"] = code
        super().__init__(status_code=status_code, detail=detail)

class UnauthorizedException(APIException):
    def __init__(self, message: str = "Unauthorized", code: str = "UNAUTHORIZED"):
        super().__init__(401, message, code)

class ForbiddenException(APIException):
    def __init__(self, message: str = "Forbidden", code: str = "FORBIDDEN"):
        super().__init__(403, message, code)

class NotFoundException(APIException):
    def __init__(self, message: str = "Not found", code: str = "NOT_FOUND"):
        super().__init__(404, message, code)

class ValidationException(APIException):
    def __init__(self, message: str = "Validation error", code: str = "VALIDATION_ERROR"):
        super().__init__(400, message, code)
```

#### password.py
```python
import re
from typing import List, Tuple

def validate_password(
    password: str,
    min_length: int = 8,
    require_uppercase: bool = True,
    require_lowercase: bool = True,
    require_digit: bool = True,
    require_special: bool = False
) -> Tuple[bool, List[str]]:
    """
    Validate password strength.

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    if len(password) < min_length:
        errors.append(f"Password must be at least {min_length} characters")

    if require_uppercase and not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")

    if require_lowercase and not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")

    if require_digit and not re.search(r"\d", password):
        errors.append("Password must contain at least one digit")

    if require_special and not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        errors.append("Password must contain at least one special character")

    return len(errors) == 0, errors
```

### 5. Configuration Module (`common/config/`)

#### base_settings.py
```python
from pydantic_settings import BaseSettings
from typing import Optional

class BaseAppSettings(BaseSettings):
    """Base settings class - extend for app-specific config"""

    # Database
    MONGODB_URI: str
    MONGODB_DATABASE: str = "app"

    # Auth
    AUTH_PROVIDER: str = "jwt"  # "jwt" or "firebase"
    JWT_SECRET: Optional[str] = None
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 30
    FIREBASE_CREDENTIALS_PATH: Optional[str] = None

    # AI
    AI_PROVIDER: str = "claude"  # "claude" or "openai"
    CLAUDE_API_KEY: Optional[str] = None
    CLAUDE_MODEL: str = "claude-sonnet-4-5-20250929"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"

    # Server
    PORT: int = 8000
    DEBUG: bool = False

    class Config:
        env_file = ".env"
        extra = "allow"  # Allow app-specific settings
```

---

## App-Specific Code (`app/`)

BrainBank-specific code that uses the common library.

### app/config.py
```python
from common.config.base_settings import BaseAppSettings

class Settings(BaseAppSettings):
    """BrainBank-specific settings"""

    # Additional databases
    HUB_MONGODB_URI: str = ""
    HUB_MONGODB_DATABASE: str = "brainbank_hub"

    # External services
    CLAUDE_API_KEY: str = ""
    ELEVENLABS_API_KEY: str = ""

    # App settings
    DAILY_EXCHANGE_LIMIT: int = 15

settings = Settings()
```

### app/models/user.py
```python
from common.database.base_document import BaseDocument
from pydantic import Field
from typing import Optional

class UserProfile(BaseDocument):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    organization: Optional[str] = None
    job_title: Optional[str] = None
    preferred_language: str = "en"

class User(BaseDocument):
    email: str
    firebase_uid: Optional[str] = None
    password_hash: Optional[str] = None  # For JWT auth
    profile: UserProfile = Field(default_factory=UserProfile)
    is_admin: bool = False

    class Settings:
        name = "users"  # MongoDB collection name
```

---

## Dependencies (requirements.txt additions)

```
# Database
beanie             # MongoDB ODM (uses motor + Pydantic)
motor              # Async MongoDB driver

# Config
pydantic-settings  # Environment configuration

# Auth - JWT (default)
python-jose[cryptography]  # JWT encoding/decoding
passlib[bcrypt]            # Password hashing

# Auth - Firebase (optional)
firebase-admin             # Firebase Admin SDK

# AI - Claude (default)
anthropic          # Anthropic Claude API

# AI - OpenAI (optional)
openai             # OpenAI API
```

## SOLID Principles Applied

1. **Single Responsibility**: Each module has one clear purpose
2. **Open/Closed**: Extend BaseDocument, AuthProvider without modifying them
3. **Liskov Substitution**: JWTAuth and FirebaseAuth are interchangeable
4. **Interface Segregation**: Small, focused interfaces
5. **Dependency Inversion**: Depend on abstractions (AuthProvider, BaseDocument)

## Decisions Made

1. **MongoDB ODM**: Using **Beanie** - integrates with Pydantic
2. **Auth Strategy**: **Both JWT+bcrypt AND Firebase** - switchable via config
3. **i18n Loading**: **Startup loading** with auto-detection of languages
4. **Separation**: Generic code in `common/`, app-specific in `app/`
5. **Reusability**: `common/` designed as standalone library for other projects
