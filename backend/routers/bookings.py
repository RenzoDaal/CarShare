from datetime import datetime, timezone
from typing import List, Optional

import emailer
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlmodel import Session, select

import schemas
from auth import get_current_user, get_session
from models import Booking, BookingStatus, Car, User
from schemas import (
    BookingReschedule,
    CarRead,
    DashboardBookingRead,
    DashboardResponse,
)
from utils import parse_iso

router = APIRouter()


@router.post("/bookings")
def create_booking(
    car_id: int,
    start_datetime: str,
    end_datetime: str,
    background_tasks: BackgroundTasks,
    distance_km: Optional[float] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    car = session.get(Car, car_id)
    if car is None:
        raise HTTPException(status_code=404, detail="Car not found")

    start_dt = parse_iso(start_datetime)
    end_dt = parse_iso(end_datetime)
    total_price = round(distance_km * car.price_per_km, 2) if distance_km is not None else None

    booking = Booking(
        car_id=car.id,
        borrower_id=current_user.id,
        start_datetime=start_dt,
        end_datetime=end_dt,
        price_per_km=car.price_per_km,
        total_km=distance_km,
        total_price=total_price,
        status=BookingStatus.PENDING.value,
    )
    session.add(booking)
    session.commit()
    session.refresh(booking)

    owner = car.owner or session.get(User, car.owner_id)
    if owner and owner.email:
        background_tasks.add_task(
            emailer.owner_booking_request_email,
            owner_email=owner.email,
            owner_name=owner.full_name,
            car_name=car.name,
            borrower_name=current_user.full_name,
            start_iso=booking.start_datetime.isoformat(),
            end_iso=booking.end_datetime.isoformat(),
            booking_id=booking.id,
        )

    if current_user.email:
        background_tasks.add_task(
            emailer.borrower_booking_confirmation_email,
            borrower_email=current_user.email,
            borrower_name=current_user.full_name,
            car_name=car.name,
            owner_name=owner.full_name if owner else "the owner",
            start_iso=booking.start_datetime.isoformat(),
            end_iso=booking.end_datetime.isoformat(),
            booking_id=booking.id,
        )

    return booking


@router.post("/bookings/{booking_id}/cancel", response_model=schemas.BookingRead)
def cancel_booking(
    booking_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    booking = session.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.borrower_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed to cancel this booking")
    if booking.status == BookingStatus.CANCELLED.value:
        raise HTTPException(status_code=400, detail="Booking is already cancelled")

    car = booking.car or session.get(Car, booking.car_id)
    if car is None:
        raise HTTPException(status_code=404, detail="Car not found")

    booking.status = BookingStatus.CANCELLED.value
    session.add(booking)
    session.commit()
    session.refresh(booking)

    return schemas.BookingRead(
        id=booking.id,
        car=CarRead(
            id=car.id,
            owner_id=car.owner_id,
            name=car.name,
            description=car.description,
            price_per_km=car.price_per_km,
            is_active=car.is_active,
            image_url=getattr(car, "image_url", None),
        ),
        start_datetime=booking.start_datetime,
        end_datetime=booking.end_datetime,
        status=booking.status,
        total_price=booking.total_price,
    )


@router.patch("/bookings/{booking_id}/reschedule", response_model=schemas.BookingRead)
def reschedule_booking(
    booking_id: int,
    body: BookingReschedule,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    booking = session.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.borrower_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed to reschedule this booking")
    if booking.status in [BookingStatus.CANCELLED.value, BookingStatus.DECLINED.value]:
        raise HTTPException(status_code=400, detail="Cannot reschedule a cancelled or declined booking")

    start_dt = parse_iso(body.start_datetime)
    end_dt = parse_iso(body.end_datetime)
    if end_dt <= start_dt:
        raise HTTPException(status_code=400, detail="End time must be after start time")

    booking.start_datetime = start_dt
    booking.end_datetime = end_dt
    booking.status = BookingStatus.PENDING.value
    if body.distance_km is not None:
        booking.total_km = body.distance_km
        booking.total_price = round(body.distance_km * booking.price_per_km, 2)
    session.add(booking)
    session.commit()
    session.refresh(booking)

    car = booking.car or session.get(Car, booking.car_id)
    if car is None:
        raise HTTPException(status_code=404, detail="Car not found")

    owner = car.owner or session.get(User, car.owner_id)
    if owner and owner.email:
        background_tasks.add_task(
            emailer.owner_booking_reschedule_email,
            owner_email=owner.email,
            owner_name=owner.full_name,
            car_name=car.name,
            borrower_name=current_user.full_name,
            start_iso=booking.start_datetime.isoformat(),
            end_iso=booking.end_datetime.isoformat(),
            booking_id=booking.id,
        )

    return schemas.BookingRead(
        id=booking.id,
        car=CarRead(
            id=car.id,
            owner_id=car.owner_id,
            name=car.name,
            description=car.description,
            price_per_km=car.price_per_km,
            is_active=car.is_active,
            image_url=getattr(car, "image_url", None),
        ),
        start_datetime=booking.start_datetime,
        end_datetime=booking.end_datetime,
        status=booking.status,
        total_price=booking.total_price,
    )


@router.get("/bookings/owner", response_model=List[DashboardBookingRead])
def list_owner_bookings(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if not current_user.role_owner:
        raise HTTPException(status_code=403, detail="Not an owner")

    bookings = session.exec(
        select(Booking)
        .join(Car)
        .where(Car.owner_id == current_user.id)
        .order_by(Booking.start_datetime.desc())
    ).all()

    result: List[DashboardBookingRead] = []
    for booking in bookings:
        car = booking.car
        if car is None:
            continue
        borrower = booking.borrower or session.get(User, booking.borrower_id)
        result.append(
            DashboardBookingRead(
                id=booking.id,
                car=CarRead(
                    id=car.id,
                    owner_id=car.owner_id,
                    name=car.name,
                    description=car.description,
                    price_per_km=car.price_per_km,
                    is_active=car.is_active,
                    image_url=getattr(car, "image_url", None),
                ),
                start_datetime=booking.start_datetime,
                end_datetime=booking.end_datetime,
                status=booking.status,
                total_price=booking.total_price,
                borrower_name=borrower.full_name if borrower else None,
                borrower_email=borrower.email if borrower else None,
            )
        )
    return result


@router.get("/bookings/borrower", response_model=List[DashboardBookingRead])
def list_borrower_bookings(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if not current_user.role_borrower:
        raise HTTPException(status_code=403, detail="Not a borrower")

    bookings = session.exec(
        select(Booking)
        .where(Booking.borrower_id == current_user.id)
        .order_by(Booking.start_datetime.desc())
    ).all()

    result: List[DashboardBookingRead] = []
    for booking in bookings:
        car = booking.car
        if car is None:
            continue
        result.append(
            DashboardBookingRead(
                id=booking.id,
                car=CarRead(
                    id=car.id,
                    owner_id=car.owner_id,
                    name=car.name,
                    description=car.description,
                    price_per_km=car.price_per_km,
                    is_active=car.is_active,
                    image_url=getattr(car, "image_url", None),
                ),
                start_datetime=booking.start_datetime,
                end_datetime=booking.end_datetime,
                status=booking.status,
                total_price=booking.total_price,
            )
        )
    return result


@router.post("/bookings/{booking_id}/accept", response_model=schemas.BookingRead)
def accept_booking(
    booking_id: int,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    booking = session.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")

    car = booking.car
    if car is None or car.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed to modify this booking")
    if booking.status != BookingStatus.PENDING.value:
        raise HTTPException(status_code=400, detail="Only pending bookings can be accepted")

    booking.status = BookingStatus.ACCEPTED.value
    session.add(booking)
    session.commit()
    session.refresh(booking)

    borrower = booking.borrower or session.get(User, booking.borrower_id)
    if borrower and borrower.email:
        background_tasks.add_task(
            emailer.borrower_booking_response_email,
            borrower_email=borrower.email,
            borrower_name=borrower.full_name,
            car_name=car.name,
            owner_name=current_user.full_name,
            start_iso=booking.start_datetime.isoformat(),
            end_iso=booking.end_datetime.isoformat(),
            booking_id=booking.id,
            status=booking.status,
        )

    return schemas.BookingRead(
        id=booking.id,
        car=CarRead(
            id=car.id,
            owner_id=car.owner_id,
            name=car.name,
            description=car.description,
            price_per_km=car.price_per_km,
            is_active=car.is_active,
            image_url=getattr(car, "image_url", None),
        ),
        start_datetime=booking.start_datetime,
        end_datetime=booking.end_datetime,
        status=booking.status,
        total_price=booking.total_price,
    )


@router.post("/bookings/{booking_id}/decline", response_model=schemas.BookingRead)
def decline_booking(
    booking_id: int,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    booking = session.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")

    car = booking.car
    if car is None or car.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed to modify this booking")
    if booking.status != BookingStatus.PENDING.value:
        raise HTTPException(status_code=400, detail="Only pending bookings can be declined")

    booking.status = BookingStatus.DECLINED.value
    session.add(booking)
    session.commit()
    session.refresh(booking)

    borrower = booking.borrower or session.get(User, booking.borrower_id)
    if borrower and borrower.email:
        background_tasks.add_task(
            emailer.borrower_booking_response_email,
            borrower_email=borrower.email,
            borrower_name=borrower.full_name,
            car_name=car.name,
            owner_name=current_user.full_name,
            start_iso=booking.start_datetime.isoformat(),
            end_iso=booking.end_datetime.isoformat(),
            booking_id=booking.id,
            status=booking.status,
        )

    return schemas.BookingRead(
        id=booking.id,
        car=CarRead(
            id=car.id,
            owner_id=car.owner_id,
            name=car.name,
            description=car.description,
            price_per_km=car.price_per_km,
            is_active=car.is_active,
            image_url=getattr(car, "image_url", None),
        ),
        start_datetime=booking.start_datetime,
        end_datetime=booking.end_datetime,
        status=booking.status,
        total_price=booking.total_price,
    )


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    now = datetime.now(timezone.utc)

    bookings = session.exec(
        select(Booking)
        .where(
            Booking.borrower_id == current_user.id,
            Booking.end_datetime >= now,
            Booking.status != BookingStatus.CANCELLED.value,
            Booking.status != BookingStatus.DECLINED.value,
        )
        .order_by(Booking.start_datetime)
    ).all()

    upcoming_bookings: List[DashboardBookingRead] = []
    for b in bookings:
        car = getattr(b, "car", None) or session.get(Car, b.car_id)
        if not car:
            continue
        upcoming_bookings.append(
            DashboardBookingRead(
                id=b.id,
                car=CarRead(
                    id=car.id,
                    owner_id=car.owner_id,
                    name=car.name,
                    description=car.description,
                    price_per_km=car.price_per_km,
                    is_active=car.is_active,
                    image_url=getattr(car, "image_url", None),
                ),
                start_datetime=b.start_datetime,
                end_datetime=b.end_datetime,
                status=str(b.status),
                total_price=getattr(b, "total_price", None),
            )
        )

    active_cars: List[CarRead] = []
    if current_user.role_owner:
        cars = session.exec(select(Car).where(Car.owner_id == current_user.id)).all()
        for car in cars:
            active_cars.append(
                CarRead(
                    id=car.id,
                    owner_id=car.owner_id,
                    name=car.name,
                    description=car.description,
                    price_per_km=car.price_per_km,
                    is_active=car.is_active,
                    image_url=getattr(car, "image_url", None),
                )
            )

    return DashboardResponse(upcoming_bookings=upcoming_bookings, active_cars=active_cars)
