from typing import Optional

from sqlmodel import SQLModel


class UserCreate(SQLModel):
    email: str
    password: str
    full_name: str
    role_owner: bool = False
    role_borrower: bool = True


class UserRead(SQLModel):
    id: int
    email: str
    full_name: str
    role_owner: bool
    role_borrower: bool


class LoginRequest(SQLModel):
    email: str
    password: str


class TokenResponse(SQLModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
