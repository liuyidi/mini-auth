import hashlib
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import RefreshToken, User
from app.schemas.auth import AuthResponse, TokenResponse, UserResponse

ALGORITHM = "HS256"


class AuthError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(user_id: uuid.UUID) -> tuple[str, int]:
    expires_minutes = settings.jwt_access_expire_minutes
    expire = datetime.now(UTC) + timedelta(minutes=expires_minutes)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "exp": expire,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)
    return token, expires_minutes * 60


def create_refresh_token(user_id: uuid.UUID) -> tuple[str, datetime, str]:
    jti = str(uuid.uuid4())
    expire = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_expire_days)
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "jti": jti,
        "exp": expire,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)
    return token, expire, hash_refresh_token(token)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise AuthError("Invalid or expired token", status_code=401) from exc


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(
        select(User).where(User.email == email.lower(), User.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


def to_user_response(user: User) -> UserResponse:
    return UserResponse.model_validate(user)


async def issue_tokens(db: AsyncSession, user: User) -> TokenResponse:
    access_token, expires_in = create_access_token(user.id)
    refresh_token, expires_at, token_hash = create_refresh_token(user.id)

    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
    )
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
    )


async def register_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    nickname: str | None,
) -> AuthResponse:
    normalized_email = email.lower()
    existing = await get_user_by_email(db, normalized_email)
    if existing is not None:
        raise AuthError("Email already registered", status_code=409)

    user = User(
        email=normalized_email,
        password_hash=hash_password(password),
        nickname=nickname or "DeepSeek 用户",
    )
    db.add(user)
    await db.flush()

    tokens = await issue_tokens(db, user)
    return AuthResponse(user=to_user_response(user), tokens=tokens)


async def login_user(db: AsyncSession, *, email: str, password: str) -> AuthResponse:
    user = await get_user_by_email(db, email)
    if user is None or not verify_password(password, user.password_hash):
        raise AuthError("Invalid email or password", status_code=401)

    tokens = await issue_tokens(db, user)
    return AuthResponse(user=to_user_response(user), tokens=tokens)


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> TokenResponse:
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise AuthError("Invalid refresh token", status_code=401)

    user_id = uuid.UUID(payload["sub"])
    token_hash = hash_refresh_token(refresh_token)

    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.user_id == user_id,
            RefreshToken.expires_at > datetime.now(UTC),
        )
    )
    stored = result.scalar_one_or_none()
    if stored is None:
        raise AuthError("Refresh token revoked or expired", status_code=401)

    user = await get_user_by_id(db, user_id)
    if user is None:
        raise AuthError("User not found", status_code=401)

    await db.delete(stored)
    await db.flush()
    return await issue_tokens(db, user)


async def logout_user(db: AsyncSession, refresh_token: str) -> None:
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise AuthError("Invalid refresh token", status_code=401)

    token_hash = hash_refresh_token(refresh_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    stored = result.scalar_one_or_none()
    if stored is not None:
        await db.delete(stored)
        await db.commit()
    else:
        await db.commit()


def get_user_id_from_access_token(token: str) -> uuid.UUID:
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise AuthError("Invalid access token", status_code=401)
    return uuid.UUID(payload["sub"])
