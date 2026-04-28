# BaseAppSettings

Base settings class for environment configuration using Pydantic Settings.

---

## Classes

### BaseAppSettings

Base settings class with common configuration options. Automatically loads values from environment variables.

**Properties:**

Database Settings:

- `MONGODB_URI` (str): MongoDB connection string. Default: "mongodb://localhost:27017"
- `MONGODB_DATABASE` (str): Database name. Default: "app"

Authentication Settings:

- `AUTH_PROVIDER` (str): "jwt" or "firebase". Default: "jwt"
- `JWT_SECRET` (Optional[str]): Secret key for JWT signing
- `JWT_ALGORITHM` (str): JWT algorithm. Default: "HS256"
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` (int): Token expiration. Default: 30
- `JWT_REFRESH_TOKEN_EXPIRE_DAYS` (int): Refresh token expiration. Default: 7
- `FIREBASE_CREDENTIALS_PATH` (Optional[str]): Path to Firebase service account JSON
- `FIREBASE_PROJECT_ID` (Optional[str]): Firebase project ID

AI Settings:

- `AI_PROVIDER` (str): "claude" or "openai". Default: "claude"
- `CLAUDE_API_KEY` (Optional[str]): Anthropic API key
- `CLAUDE_MODEL` (str): Claude model. Default: "claude-sonnet-4-5-20250929"
- `OPENAI_API_KEY` (Optional[str]): OpenAI API key
- `OPENAI_MODEL` (str): OpenAI model. Default: "gpt-4o"
- `OPENAI_EMBEDDING_MODEL` (str): Embedding model. Default: "text-embedding-3-small"

Server Settings:

- `HOST` (str): Server host. Default: "0.0.0.0"
- `PORT` (int): Server port. Default: 8000
- `DEBUG` (bool): Debug mode. Default: False
- `ENVIRONMENT` (str): "development", "staging", or "production". Default: "development"
- `CORS_ORIGINS` (str): Comma-separated origins or "_". Default: "_"
- `CORS_ALLOW_CREDENTIALS` (bool): Allow credentials. Default: True

Internationalization:

- `DEFAULT_LANGUAGE` (str): Default language code. Default: "en"
- `SUPPORTED_LANGUAGES` (str): Comma-separated language codes. Default: "en,sv"

**Methods:**

#### get_cors_origins

- **Inputs:** None
- **Outputs:** (list) List of allowed CORS origins
- **Description:** Parse CORS_ORIGINS string into a list

#### get_supported_languages

- **Inputs:** None
- **Outputs:** (list) List of supported language codes
- **Description:** Parse SUPPORTED_LANGUAGES string into a list

#### is_production

- **Inputs:** None
- **Outputs:** (bool) True if running in production
- **Description:** Check if running in production environment

#### is_development

- **Inputs:** None
- **Outputs:** (bool) True if running in development
- **Description:** Check if running in development environment

#### validate_required

- **Inputs:** None
- **Outputs:** (None)
- **Description:** Validate that required settings are configured. Raises ValueError if required settings are missing based on AUTH_PROVIDER and AI_PROVIDER values.
