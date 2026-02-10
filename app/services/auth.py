from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.models.auth import TokenPayload, UserInDB

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# In-memory fake user store — swap for a real DB later
FAKE_USERS_DB: dict[str, UserInDB] = {
    "admin": UserInDB(
        username="admin",
        hashed_password=pwd_context.hash("changeme123"),
    ),
}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_user(username: str) -> UserInDB | None:
    return FAKE_USERS_DB.get(username)


def authenticate_user(username: str, password: str) -> UserInDB | None:
    user = get_user(username)
    if user is None or not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(
    subject: str, secret_key: str, algorithm: str, expires_minutes: int
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    payload = TokenPayload(sub=subject, exp=int(expire.timestamp()))
    return jwt.encode(payload.model_dump(), secret_key, algorithm=algorithm)


def decode_access_token(
    token: str, secret_key: str, algorithm: str
) -> TokenPayload | None:
    try:
        data = jwt.decode(token, secret_key, algorithms=[algorithm])
        return TokenPayload(**data)
    except JWTError:
        return None
