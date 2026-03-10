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
    is_admin: bool
    timezone: str = "Europe/Amsterdam"
    notification_prefs: Optional[str] = None


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
    borrower_name: Optional[str] = None
    borrower_email: Optional[str] = None
    stops: Optional[List[str]] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    last_reminder_sent: Optional[datetime] = None


class BookingReschedule(SQLModel):
    start_datetime: str
    end_datetime: str
    distance_km: Optional[float] = None
    stops: Optional[List[str]] = None
    notes: Optional[str] = None


class DashboardResponse(SQLModel):
    upcoming_bookings: List[DashboardBookingRead]
    active_cars: List[CarRead]
    active_rentals: List[DashboardBookingRead] = []


class BookingRead(SQLModel):
    id: int
    car: CarRead
    start_datetime: datetime
    end_datetime: datetime
    status: str
    total_price: Optional[float] = None


class RequestPasswordReset(SQLModel):
    email: str


class ResetPassword(SQLModel):
    token: str
    new_password: str


class UserUpdate(SQLModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    role_owner: Optional[bool] = None
    role_borrower: Optional[bool] = None
    timezone: Optional[str] = None
    notification_prefs: Optional[str] = None


class ChangePassword(SQLModel):
    current_password: str
    new_password: str


class CarStatsRead(SQLModel):
    car_id: int
    car_name: str
    total_bookings: int
    total_km: float
    total_earnings: float


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


class WaitlistCreate(SQLModel):
    car_id: int
    start_datetime: str
    end_datetime: str


class WaitlistRead(SQLModel):
    id: int
    car_id: int
    car_name: str
    start_datetime: datetime
    end_datetime: datetime
    created_at: datetime


class NotificationRead(SQLModel):
    id: int
    message: str
    is_read: bool
    created_at: datetime
    booking_id: Optional[int] = None


class CarImageRead(SQLModel):
    id: int
    car_id: int
    url: str
    order: int


class CoOwnerRead(SQLModel):
    user_id: int
    full_name: str
    email: str
    status: str  # "pending" | "accepted"


class CoOwnerInvite(SQLModel):
    email: str


class CoOwnerInviteRead(SQLModel):
    car_id: int
    car_name: str
    owner_name: str
    status: str
