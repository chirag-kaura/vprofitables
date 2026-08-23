# core/auth.py
import datetime
import os
import jwt
import bcrypt

# ── JWT Secret ───────────────────────────────────────────────────────────────────
# Set JWT_SECRET env var in production. Never commit a real secret to git.
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET = os.environ.get(
    "JWT_SECRET",
    "dev-only-change-before-production-do-not-use-in-prod"
)
JWT_ALGORITHM = "HS256"

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False

def create_access_token(user_id: str, email: str, role: str = "USER", expires_delta_days: int = 7) -> str:
    payload = {
        "user_id": user_id,
        "email": email,
        "role": role,
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=expires_delta_days)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_access_token(token: str) -> dict:
    """Decodes JWT access token. Returns payload dict if valid, or None."""
    try:
        if token.startswith("Bearer "):
            token = token[7:]
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
