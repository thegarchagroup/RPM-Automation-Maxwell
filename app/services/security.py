import bcrypt


def hash_password(password: str) -> str:
    """Hash a password using bcrypt with random salt."""
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against the stored bcrypt hash with graceful legacy fallback."""
    if not plain_password or not hashed_password:
        return False
    try:
        pwd_bytes = plain_password.encode("utf-8")[:72]
        if hashed_password.startswith("$2b$") or hashed_password.startswith("$2a$"):
            return bcrypt.checkpw(pwd_bytes, hashed_password.encode("utf-8"))
        # Fallback for transitioning legacy plaintext entries
        return plain_password == hashed_password
    except Exception:
        return False
