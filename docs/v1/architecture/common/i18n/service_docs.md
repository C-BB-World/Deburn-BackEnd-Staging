# I18nService

Generic internationalization (i18n) service.

---

## Classes

### I18nService

Generic internationalization service. Loads translations from JSON files at startup and provides fast lookup with fallback.

**Properties:**

- `locales_dir` (Path): Path to the locales directory
- `default_language` (str): Default language code for fallback
- `fallback_to_key` (bool): If True, return key when translation not found
- `translations` (Dict[str, Dict[str, Any]]): Loaded translations
- `supported_languages` (List[str]): List of supported language codes

**Methods:**

#### __init__

- **Inputs:**
  - `locales_dir` (str): Path to the locales directory
  - `default_language` (str): Default language code. Default: "en"
  - `supported_languages` (Optional[List[str]]): List of supported languages. Auto-detects if None.
  - `fallback_to_key` (bool): Return key when not found. Default: True
- **Outputs:** (I18nService) New I18nService instance
- **Description:** Initialize i18n service and load all translations at startup.

#### t

- **Inputs:**
  - `key` (str): Dot notation key (e.g., 'auth.login.success'). First part is namespace (filename without .json).
  - `language` (Optional[str]): Language code. Falls back to default if not supported.
  - `**options` (Any): Interpolation values. Special keys: count (pluralization), default (fallback value)
- **Outputs:** (str) Translated string, or the key if not found
- **Description:** Get translation by dot-notation key. Supports variable interpolation with {{var}} or {var} format. Supports pluralization with count option (uses 'zero', 'one', 'few', 'many', 'other' forms).

#### has

- **Inputs:**
  - `key` (str): Dot notation key
  - `language` (Optional[str]): Language to check. Defaults to default_language.
- **Outputs:** (bool) True if the key exists
- **Description:** Check if a translation key exists.

#### is_supported

- **Inputs:**
  - `language` (str): Language code to check
- **Outputs:** (bool) True if language is supported
- **Description:** Check if a language is supported.

#### get_languages

- **Inputs:** None
- **Outputs:** (List[str]) List of supported language codes
- **Description:** Get list of supported languages.

#### get_namespace

- **Inputs:**
  - `namespace` (str): Namespace name (e.g., 'common', 'auth')
  - `language` (Optional[str]): Language code
- **Outputs:** (Dict[str, Any]) Dictionary of all translations in the namespace
- **Description:** Get all translations for a namespace. Useful for sending translations to frontend.

#### get_all

- **Inputs:**
  - `language` (Optional[str]): Language code
- **Outputs:** (Dict[str, Any]) Dictionary of all namespaces and their translations
- **Description:** Get all translations for a language.

#### reload

- **Inputs:** None
- **Outputs:** (None)
- **Description:** Reload all translations from disk.
