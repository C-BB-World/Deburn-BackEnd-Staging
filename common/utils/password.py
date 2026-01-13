"""
Password strength validation.

Configurable password validation with support for various requirements.

Example:
    from common.utils import validate_password

    # Basic validation
    is_valid, errors = validate_password("weakpass")
    if not is_valid:
        print("Password errors:", errors)

    # Custom requirements
    is_valid, errors = validate_password(
        "MyP@ss123",
        min_length=10,
        require_special=True,
    )
"""

import re
from typing import List, Tuple, Optional


def validate_password(
    password: str,
    min_length: int = 8,
    max_length: int = 128,
    require_uppercase: bool = True,
    require_lowercase: bool = True,
    require_digit: bool = True,
    require_special: bool = False,
    special_chars: str = r"!@#$%^&*(),.?\":{}|<>",
    disallowed_patterns: Optional[List[str]] = None,
) -> Tuple[bool, List[str]]:
    """
    Validate password strength.

    Args:
        password: The password to validate
        min_length: Minimum password length
        max_length: Maximum password length
        require_uppercase: Require at least one uppercase letter
        require_lowercase: Require at least one lowercase letter
        require_digit: Require at least one digit
        require_special: Require at least one special character
        special_chars: String of allowed special characters
        disallowed_patterns: List of regex patterns that are not allowed

    Returns:
        Tuple of (is_valid: bool, errors: List[str])

    Examples:
        >>> is_valid, errors = validate_password("weak")
        >>> print(is_valid)
        False
        >>> print(errors)
        ['Password must be at least 8 characters', ...]

        >>> is_valid, errors = validate_password("StrongP@ss123")
        >>> print(is_valid)
        True
    """
    errors: List[str] = []

    # Check length
    if len(password) < min_length:
        errors.append(f"Password must be at least {min_length} characters")

    if len(password) > max_length:
        errors.append(f"Password must be no more than {max_length} characters")

    # Check character requirements
    if require_uppercase and not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")

    if require_lowercase and not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")

    if require_digit and not re.search(r"\d", password):
        errors.append("Password must contain at least one digit")

    if require_special:
        # Escape special regex characters in the special_chars string
        escaped_chars = re.escape(special_chars)
        if not re.search(f"[{escaped_chars}]", password):
            errors.append("Password must contain at least one special character")

    # Check disallowed patterns
    if disallowed_patterns:
        for pattern in disallowed_patterns:
            if re.search(pattern, password, re.IGNORECASE):
                errors.append("Password contains disallowed pattern")
                break

    return len(errors) == 0, errors


def check_common_passwords(
    password: str,
    common_passwords: Optional[List[str]] = None,
) -> bool:
    """
    Check if password is in a list of common passwords.

    Args:
        password: The password to check
        common_passwords: List of common passwords. If None, uses built-in list.

    Returns:
        True if password is common (should be rejected)
    """
    if common_passwords is None:
        # Built-in list of very common passwords
        common_passwords = [
            "123456",
            "password",
            "12345678",
            "qwerty",
            "123456789",
            "12345",
            "1234",
            "111111",
            "1234567",
            "dragon",
            "123123",
            "baseball",
            "iloveyou",
            "trustno1",
            "sunshine",
            "princess",
            "football",
            "welcome",
            "shadow",
            "superman",
            "michael",
            "ninja",
            "mustang",
            "password1",
            "password123",
            "admin",
            "letmein",
            "monkey",
            "abc123",
            "starwars",
        ]

    return password.lower() in [p.lower() for p in common_passwords]


def calculate_password_strength(password: str) -> dict:
    """
    Calculate password strength score and feedback.

    Args:
        password: The password to analyze

    Returns:
        Dictionary with:
            - score: 0-4 (0=very weak, 4=very strong)
            - feedback: List of suggestions for improvement
            - is_strong: Boolean indicating if password is acceptably strong
    """
    score = 0
    feedback = []

    # Length scoring
    if len(password) >= 8:
        score += 1
    if len(password) >= 12:
        score += 1
    if len(password) >= 16:
        score += 1

    if len(password) < 8:
        feedback.append("Use at least 8 characters")
    elif len(password) < 12:
        feedback.append("Consider using 12+ characters for better security")

    # Character variety
    has_lower = bool(re.search(r"[a-z]", password))
    has_upper = bool(re.search(r"[A-Z]", password))
    has_digit = bool(re.search(r"\d", password))
    has_special = bool(re.search(r"[!@#$%^&*(),.?\":{}|<>]", password))

    variety = sum([has_lower, has_upper, has_digit, has_special])

    if variety >= 3:
        score += 1

    if not has_upper:
        feedback.append("Add uppercase letters")
    if not has_lower:
        feedback.append("Add lowercase letters")
    if not has_digit:
        feedback.append("Add numbers")
    if not has_special:
        feedback.append("Add special characters (!@#$%^&*)")

    # Check for common patterns
    if re.search(r"(.)\1{2,}", password):
        feedback.append("Avoid repeating characters")
        score = max(0, score - 1)

    if re.search(r"(012|123|234|345|456|567|678|789|890)", password):
        feedback.append("Avoid sequential numbers")
        score = max(0, score - 1)

    if re.search(r"(abc|bcd|cde|def|efg|fgh|ghi|hij)", password.lower()):
        feedback.append("Avoid sequential letters")
        score = max(0, score - 1)

    # Check if it's a common password
    if check_common_passwords(password):
        feedback.append("This is a commonly used password")
        score = 0

    return {
        "score": min(4, score),
        "feedback": feedback,
        "is_strong": score >= 2,
    }
