from datetime import datetime, timedelta, timezone
from importlib import import_module
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

from app.core.config import get_settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/token")


class TokenUser(BaseModel):
    user_id: str
    email: str
    role: str


def create_access_token(user: TokenUser) -> str:
    settings = get_settings()
    jwt = import_module("jose.jwt")
    secret = settings.resolve_jwt_secret()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": user.user_id,
        "email": user.email,
        "role": user.role,
        "exp": expire,
    }
    return jwt.encode(payload, secret, algorithm=settings.jwt_algorithm)


def parse_token(token: str) -> TokenUser:
    settings = get_settings()
    jwt = import_module("jose.jwt")
    jwt_error_cls = getattr(import_module("jose"), "JWTError")
    secret = settings.resolve_jwt_secret()

    try:
        payload = jwt.decode(token, secret, algorithms=[settings.jwt_algorithm])
        user_id = payload.get("sub")
        email = payload.get("email")
        role = payload.get("role", "user")
        if not user_id or not email:
            raise ValueError("Invalid token claims")
        return TokenUser(user_id=user_id, email=email, role=role)
    except (jwt_error_cls, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials") from exc


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> TokenUser:
    settings = get_settings()
    jwt = import_module("jose.jwt")
    jwt_error_cls = getattr(import_module("jose"), "JWTError")
    secret = settings.resolve_jwt_secret()
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )

    try:
        payload = jwt.decode(token, secret, algorithms=[settings.jwt_algorithm])
        user_id = payload.get("sub")
        email = payload.get("email")
        role = payload.get("role", "user")
        if not user_id or not email:
            raise credentials_error
        return TokenUser(user_id=user_id, email=email, role=role)
    except jwt_error_cls as exc:
        raise credentials_error from exc


def require_roles(*allowed_roles: str):
    async def role_guard(user: Annotated[TokenUser, Depends(get_current_user)]) -> TokenUser:
        if user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user

    return role_guard
