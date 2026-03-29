# Password Utilities

Password strength validation utilities.

---

## Functions

### validate_password

- **Inputs:**
  - `password` (str): The password to validate
  - `min_length` (int): Minimum length. Default: 8
  - `max_length` (int): Maximum length. Default: 128
  - `require_uppercase` (bool): Require uppercase letter. Default: True
  - `require_lowercase` (bool): Require lowercase letter. Default: True
  - `require_digit` (bool): Require digit. Default: True
  - `require_special` (bool): Require special character. Default: False
  - `special_chars` (str): Allowed special characters. Default: r"!@#$%^&*(),.?\":{}|<>"
  - `disallowed_patterns` (Optional[List[str]]): Regex patterns that are not allowed
- **Outputs:** (Tuple[bool, List[str]]) Tuple of (is_valid, errors list)
- **Description:** Validate password strength against configurable requirements.

---

### check_common_passwords

- **Inputs:**
  - `password` (str): The password to check
  - `common_passwords` (Optional[List[str]]): List of common passwords. Uses built-in list if None.
- **Outputs:** (bool) True if password is common (should be rejected)
- **Description:** Check if password is in a list of common passwords (e.g., "123456", "password").

---

### calculate_password_strength

- **Inputs:**
  - `password` (str): The password to analyze
- **Outputs:** (dict) Dictionary with:
  - `score` (int): 0-4 (0=very weak, 4=very strong)
  - `feedback` (List[str]): List of suggestions for improvement
  - `is_strong` (bool): True if password is acceptably strong (score >= 2)
- **Description:** Calculate password strength score and feedback. Analyzes length, character variety, common patterns, and common passwords.
