from datetime import date, datetime
from typing import List, Optional

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
    is_approved: bool


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


class DashboardBookingRead(SQLModel):
    id: int
    car: CarRead
    start_datetime: datetime
    end_datetime: datetime
    status: str
    total_price: Optional[float] = None


class DashboardResponse(SQLModel):
    upcoming_bookings: List[DashboardBookingRead]
    active_cars: List[CarRead]


class BookingRead(SQLModel):
    id: int
    car: CarRead
    start_datetime: datetime
    end_datetime: datetime
    status: str
    total_price: Optional[float] = None


class CarUnavailabilityCreate(SQLModel):
    start_date: date
    end_date: date


class CarUnavailabilityRead(SQLModel):
    id: int
    car_id: int
    start_date: date
    end_date: date


class CalendarDateRange(SQLModel):
    start: date
    end: date
