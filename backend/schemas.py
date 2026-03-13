from datetime import date, datetime
from typing import List, Optional

from pydantic import Field
from sqlmodel import SQLModel


class UserCreate(SQLModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)
    full_name: str = Field(max_length=100)
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
    name: str = Field(max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    price_per_km: float
    price_mode: str = "manual"
    fuel_type: Optional[str] = None
    calc_battery_kwh: Optional[float] = None
    calc_range_km: Optional[float] = None
    calc_charge_cost_per_kwh: Optional[float] = None
    calc_consumption_per_100km: Optional[float] = None
    calc_fuel_price_per_liter: Optional[float] = None


class CarRead(SQLModel):
    id: int
    owner_id: int
    name: str
    description: Optional[str] = None
    price_per_km: float
    is_active: bool
    image_url: Optional[str] = None
    price_mode: str = "manual"
    fuel_type: Optional[str] = None
    calc_battery_kwh: Optional[float] = None
    calc_range_km: Optional[float] = None
    calc_charge_cost_per_kwh: Optional[float] = None
    calc_consumption_per_100km: Optional[float] = None
    calc_fuel_price_per_liter: Optional[float] = None


class CarUpdate(SQLModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    price_per_km: Optional[float] = None
    is_active: Optional[bool] = None
    image_url: Optional[str] = None
    price_mode: Optional[str] = None
    fuel_type: Optional[str] = None
    calc_battery_kwh: Optional[float] = None
    calc_range_km: Optional[float] = None
    calc_charge_cost_per_kwh: Optional[float] = None
    calc_consumption_per_100km: Optional[float] = None
    calc_fuel_price_per_liter: Optional[float] = None


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
    route_coordinates: Optional[List[List[float]]] = None
    created_at: Optional[datetime] = None
    last_reminder_sent: Optional[datetime] = None


class BookingReschedule(SQLModel):
    start_datetime: str
    end_datetime: str
    distance_km: Optional[float] = None
    stops: Optional[List[str]] = None
    notes: Optional[str] = Field(None, max_length=2000)


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


class BorrowerStatsRead(SQLModel):
    total_rides: int
    total_km: float
    total_spent: float
    favourite_car: Optional[str] = None


class DayBusySlot(SQLModel):
    start: datetime
    end: datetime
    type: str  # "booking" | "block"


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
