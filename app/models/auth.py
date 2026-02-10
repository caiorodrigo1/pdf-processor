from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str
    exp: int


class UserBase(BaseModel):
    username: str


class UserInDB(UserBase):
    hashed_password: str
    email: str = ""
    is_verified: bool = False


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str


class RegisterResponse(BaseModel):
    message: str
    username: str
    email: str
