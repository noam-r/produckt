"""
Password validation utilities for enforcing strong passwords.
"""

import re
from typing import List, Tuple


class PasswordValidationError(Exception):
    """Raised when password doesn't meet requirements."""
    pass


def validate_password_complexity(password: str) -> Tuple[bool, List[str]]:
    """
    Validate password meets complexity requirements.

    Requirements:
    - At least 8 characters long
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character (!@#$%^&*(),.?":{}|<>)
    - Not a common weak password

    Args:
        password: The password to validate

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Length check
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")

    # Uppercase check
    if not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")

    # Lowercase check
    if not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")

    # Digit check
    if not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one digit")

    # Special character check
    special_chars = r'!@#$%^&*(),.?":{}|<>'
    if not any(c in special_chars for c in password):
        errors.append("Password must contain at least one special character (!@#$%^&*(),.?\":{}|<>)")

    # Common weak passwords check
    weak_passwords = [
        'password', 'password123', '12345678', 'qwerty', 'abc123',
        'password1', '123456789', 'admin123', 'letmein', 'welcome',
        '1234', '1111', '0000', 'admin', 'root', 'test',
    ]
    if password.lower() in weak_passwords:
        errors.append("This password is too common and easy to guess")

    # Sequential characters check
    if re.search(r'(012|123|234|345|456|567|678|789|890|abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)', password.lower()):
        errors.append("Password should not contain sequential characters")

    # Repeated characters check
    if re.search(r'(.)\1{2,}', password):
        errors.append("Password should not contain more than 2 repeated characters")

    return (len(errors) == 0, errors)


def validate_password_or_raise(password: str) -> str:
    """
    Validate password and raise exception if invalid.

    Args:
        password: The password to validate

    Returns:
        The password if valid

    Raises:
        PasswordValidationError: If password doesn't meet requirements
    """
    is_valid, errors = validate_password_complexity(password)
    if not is_valid:
        raise PasswordValidationError("; ".join(errors))
    return password
