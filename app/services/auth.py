from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.models.auth import TokenPayload

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


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
