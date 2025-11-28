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


class CarCreate(SQLModel):
    name: str
    description: Optional[str] = None
    price_per_km: float


class CarRead(SQLModel):
    id: int
    owner_id: int
    name: str
    description: Optional[str] = None
    price_per_km: float
    is_active: bool
    image_url: Optional[str] = None


class CarUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price_per_km: Optional[float] = None
    is_active: Optional[bool] = None
    image_url: Optional[str] = None
