from datetime import date, datetime, timezone
from enum import Enum
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel, Column, String


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    password_hash: str
    full_name: str
    role_owner: bool = False
    role_borrower: bool = True
    is_approved: bool = False
    is_admin: bool = False
    timezone: str = Field(default="Europe/Amsterdam")
    notification_prefs: Optional[str] = Field(default=None)  # JSON

    cars: List["Car"] = Relationship(back_populates="owner")
    bookings: List["Booking"] = Relationship(back_populates="borrower")


class Car(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id")
    name: str
    description: Optional[str] = None
    price_per_km: float
    is_active: bool = True
    image_url: Optional[str] = None

    owner: Optional[User] = Relationship(back_populates="cars")
    bookings: List["Booking"] = Relationship(back_populates="car")
    unavailabilities: List["CarUnavailability"] = Relationship(back_populates="car")


class BookingStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    CANCELLED = "cancelled"


class CarUnavailability(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    car_id: int = Field(foreign_key="car.id")
    start_date: date
    end_date: date

    car: Optional[Car] = Relationship(back_populates="unavailabilities")


class PasswordResetToken(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    token: str = Field(sa_column=Column(String, unique=True, index=True))
    expires_at: datetime


class CarImage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    car_id: int = Field(foreign_key="car.id")
    url: str
    order: int = 0


class Waitlist(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    car_id: int = Field(foreign_key="car.id")
    user_id: int = Field(foreign_key="user.id")
    start_datetime: datetime
    end_datetime: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CarCoOwner(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    car_id: int = Field(foreign_key="car.id")
    user_id: int = Field(foreign_key="user.id")
    status: str = Field(default="pending")  # "pending" | "accepted"
    added_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Notification(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    message: str
    is_read: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    booking_id: Optional[int] = None


class PushSubscription(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    endpoint: str = Field(sa_column=Column(String, unique=True, index=True))
    p256dh: str
    auth: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Booking(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    car_id: int = Field(foreign_key="car.id")
    borrower_id: int = Field(foreign_key="user.id")

    start_datetime: datetime
    end_datetime: datetime

    total_km: Optional[float] = None
    price_per_km: float
    total_price: Optional[float] = None
    stops_json: Optional[str] = None  # JSON-encoded list of stop strings
    notes: Optional[str] = None

    status: str = Field(default=BookingStatus.PENDING.value)
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_reminder_sent: Optional[datetime] = Field(default=None)

    car: Optional[Car] = Relationship(back_populates="bookings")
    borrower: Optional[User] = Relationship(back_populates="bookings")
