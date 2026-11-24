import re

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_]{3,50}$")

def validate_registration_input(data: dict) -> tuple[bool, str | None]:
    if not data:
        return False, "Request body cannot be empty"

    full_name = data.get("full_name", "").strip()
    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not full_name:
        return False, "Full name is required"
    if len(full_name) > 100:
        return False, "Full name cannot exceed 100 characters"

    if not username:
        return False, "Username is required"
    if not USERNAME_REGEX.match(username):
        return False, "Username must be 3-50 characters long and contain only letters, numbers, and underscores"

    if not email:
        return False, "Email address is required"
    if not EMAIL_REGEX.match(email):
        return False, "Invalid email address format"

    if not password:
        return False, "Password is required"
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"

    return True, None

def validate_login_input(data: dict) -> tuple[bool, str | None]:
    if not data:
        return False, "Request body cannot be empty"

    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not email:
        return False, "Email address is required"
    if not EMAIL_REGEX.match(email):
        return False, "Invalid email address format"
    if not password:
        return False, "Password is required"

    return True, None

