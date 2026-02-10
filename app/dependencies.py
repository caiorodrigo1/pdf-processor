from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import Settings
from app.services.auth import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

limiter = Limiter(key_func=get_remote_address)


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_current_user(
    request: Request,
    token: Annotated[str, Depends(oauth2_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> str:
    payload = decode_access_token(
        token, settings.jwt_secret_key, settings.jwt_algorithm
    )
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    firestore_svc = request.app.state.firestore_service
    user_data = firestore_svc.get_user(payload.sub) if firestore_svc else None
    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user_data.get("is_verified", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified",
        )

    return user_data["username"]
