from datetime import date, datetime, time
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    password_hash: str
    full_name: str
    role_owner: bool = False
    role_borrower: bool = True

    cars: List["Car"] = Relationship(back_populates="owner")
    bookings: List["Booking"] = Relationship(back_populates="borrower")


class Car(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id")
    name: str
    description: Optional[str] = None
    price_per_km: float
    is_active: bool = True

    owner: Optional[User] = Relationship(back_populates="cars")
    availabilities: List["CarAvailability"] = Relationship(back_populates="car")
    bookings: List["Booking"] = Relationship(back_populates="car")


class CarAvailability(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    car_id: int = Field(foreign_key="car.id")
    start_datetime: datetime
    end_datetime: datetime
    car: Optional[Car] = Relationship(back_populates="availabilities")


class BookingStatus:
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    PAID = "PAID"
    CANCELLED = "CANCELLED"


class Booking(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    car_id: int = Field(foreign_key="car.id")
    borrower_id: int = Field(foreign_key="user.id")

    start_datetime: datetime
    end_datetime: datetime

    total_km: Optional[float] = None
    price_per_km: float
    total_price: Optional[float] = None

    status: str = Field(default=BookingStatus.PENDING)

    car: Optional[Car] = Relationship(back_populates="bookings")
    borrower: Optional[User] = Relationship(back_populates="bookings")
    route_stops: List["RouteStop"] = Relationship(back_populates="booking")
    payment: Optional["Payment"] = Relationship(back_populates="booking")


class RouteStop(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    booking_id: int = Field(foreign_key="booking.id")

    order: int
    label: str
    lat: Optional[float] = None
    lng: Optional[float] = None

    booking: Optional[Booking] = Relationship(back_populates="route_stops")


class Payment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    booking_id: int = Field(foreign_key="booking.id")
    provider: str
    provider_payment_id: str
    amount: float
    currency: str = "EUR"
    status: str

    booking: Optional[Booking] = Relationship(back_populates="payment")
