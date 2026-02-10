import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from app.config import Settings
from app.dependencies import get_settings
from app.models.auth import RegisterRequest, RegisterResponse, Token
from app.services.auth import (
    create_access_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    settings: Annotated[Settings, Depends(get_settings)],
    request: Request,
) -> Token:
    firestore_svc = request.app.state.firestore_service
    user_data = firestore_svc.get_user(form_data.username) if firestore_svc else None

    if user_data is None or not verify_password(
        form_data.password, user_data["hashed_password"]
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user_data.get("is_verified", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please check your inbox.",
        )

    access_token = create_access_token(
        subject=user_data["username"],
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expires_minutes=settings.jwt_expire_minutes,
    )
    return Token(access_token=access_token)


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    body: RegisterRequest,
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> RegisterResponse:
    firestore_svc = request.app.state.firestore_service
    if firestore_svc is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User storage unavailable",
        )

    # Check username not taken
    if firestore_svc.get_user(body.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )

    # Check email not taken
    if firestore_svc.get_user_by_email(body.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    verification_token = str(uuid.uuid4())

    firestore_svc.save_user(
        body.username,
        {
            "username": body.username,
            "email": body.email,
            "hashed_password": hash_password(body.password),
            "is_verified": False,
            "verification_token": verification_token,
        },
    )

    # Send verification email
    email_svc = getattr(request.app.state, "email_service", None)
    if email_svc:
        base_url = str(request.base_url).rstrip("/")
        await email_svc.send_verification_email(
            to_email=body.email,
            username=body.username,
            token=verification_token,
            base_url=base_url,
        )

    return RegisterResponse(
        message="Registration successful. Please check your email to verify.",
        username=body.username,
        email=body.email,
    )


@router.get("/verify")
async def verify_email(token: str, request: Request) -> dict:
    firestore_svc = request.app.state.firestore_service
    if firestore_svc is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User storage unavailable",
        )

    user_data = firestore_svc.get_user_by_verification_token(token)
    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )

    firestore_svc.update_user(
        user_data["username"],
        {"is_verified": True, "verification_token": ""},
    )

    return {"message": "Email verified successfully. You can now log in."}
