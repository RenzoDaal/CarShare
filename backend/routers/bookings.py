import json
from datetime import datetime, timezone
from typing import List, Optional

import emailer
import schemas
from auth import get_current_user, get_session
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from models import Booking, BookingStatus, Car, CarCoOwner, User, Waitlist
from routers.notifications import create_notification, send_web_push_task
from schemas import (BookingReschedule, BorrowerStatsRead, CarRead,
                     DashboardBookingRead, DashboardResponse)
from sqlmodel import Session, select
from utils import get_managed_car_ids, get_prefs, is_car_manager, parse_iso

router = APIRouter()


def _parse_stops(stops_json: Optional[str]) -> Optional[List[str]]:
    if not stops_json:
        return None
    try:
        return json.loads(stops_json)
    except Exception:
        return None


def _parse_coordinates(coords_json: Optional[str]) -> Optional[List[List[float]]]:
    if not coords_json:
        return None
    try:
        return json.loads(coords_json)
    except Exception:
        return None


@router.post("/bookings")
def create_booking(
    car_id: int,
    start_datetime: str,
    end_datetime: str,
    background_tasks: BackgroundTasks,
    distance_km: Optional[float] = None,
    stops: Optional[str] = None,
    notes: Optional[str] = None,
    route_coordinates: Optional[str] = None,
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
        stops_json=stops,
        notes=notes,
        route_coordinates_json=route_coordinates,
        status=BookingStatus.PENDING.value,
    )
    session.add(booking)
    session.commit()
    session.refresh(booking)

    try:
        owner = car.owner or session.get(User, car.owner_id)
        if owner:
            owner_prefs = get_prefs(owner)
            if owner_prefs["booking_request"]["push"]:
                create_notification(
                    session,
                    owner.id,
                    f"New booking request for {car.name} from {current_user.full_name}",
                    booking.id,
                )
                background_tasks.add_task(send_web_push_task, owner.id, f"New booking request for {car.name} from {current_user.full_name}")
            session.commit()
            if owner_prefs["booking_request"]["email"] and owner.email:
                background_tasks.add_task(
                    emailer.owner_booking_request_email,
                    owner_email=owner.email,
                    owner_name=owner.full_name,
                    car_name=car.name,
                    borrower_name=current_user.full_name,
                    start_iso=booking.start_datetime.isoformat(),
                    end_iso=booking.end_datetime.isoformat(),
                    booking_id=booking.id,
                    notes=booking.notes,
                    tz=getattr(owner, "timezone", "Europe/Amsterdam"),
                )

        co_owners = session.exec(
            select(CarCoOwner).where(CarCoOwner.car_id == car.id, CarCoOwner.status == "accepted")
        ).all()
        for co in co_owners:
            co_user = session.get(User, co.user_id)
            if co_user:
                co_prefs = get_prefs(co_user)
                if co_prefs["booking_request"]["push"]:
                    create_notification(
                        session,
                        co_user.id,
                        f"New booking request for {car.name} from {current_user.full_name}",
                        booking.id,
                    )
                    background_tasks.add_task(send_web_push_task, co_user.id, f"New booking request for {car.name} from {current_user.full_name}")
                if co_prefs["booking_request"]["email"] and co_user.email:
                    background_tasks.add_task(
                        emailer.owner_booking_request_email,
                        owner_email=co_user.email,
                        owner_name=co_user.full_name,
                        car_name=car.name,
                        borrower_name=current_user.full_name,
                        start_iso=booking.start_datetime.isoformat(),
                        end_iso=booking.end_datetime.isoformat(),
                        booking_id=booking.id,
                        notes=booking.notes,
                        tz=getattr(co_user, "timezone", "Europe/Amsterdam"),
                    )

        borrower_prefs = get_prefs(current_user)
        if borrower_prefs["booking_request"]["email"] and current_user.email:
            background_tasks.add_task(
                emailer.borrower_booking_confirmation_email,
                borrower_email=current_user.email,
                borrower_name=current_user.full_name,
                car_name=car.name,
                owner_name=owner.full_name if owner else "the owner",
                start_iso=booking.start_datetime.isoformat(),
                end_iso=booking.end_datetime.isoformat(),
                booking_id=booking.id,
                tz=getattr(current_user, "timezone", "Europe/Amsterdam"),
            )

        session.commit()

    except Exception as e:
        # log this, but do not fail booking creation
        print(f"Post-booking notification error: {e}")

    return {"id": booking.id}

@router.post("/bookings/{booking_id}/cancel", response_model=schemas.BookingRead)
def cancel_booking(
    booking_id: int,
    background_tasks: BackgroundTasks,
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
    owner = car.owner or session.get(User, car.owner_id)
    session.add(booking)
    if owner:
        owner_prefs = get_prefs(owner)
        if owner_prefs["booking_cancelled"]["push"]:
            create_notification(
                session,
                owner.id,
                f"{current_user.full_name} cancelled their booking for {car.name}",
                booking.id,
            )
            background_tasks.add_task(send_web_push_task, owner.id, f"{current_user.full_name} cancelled their booking for {car.name}")
        if owner_prefs["booking_cancelled"]["email"] and owner.email:
            background_tasks.add_task(
                emailer.owner_booking_cancelled_email,
                owner_email=owner.email,
                owner_name=owner.full_name,
                car_name=car.name,
                borrower_name=current_user.full_name,
                start_iso=booking.start_datetime.isoformat(),
                end_iso=booking.end_datetime.isoformat(),
                booking_id=booking.id,
                tz=getattr(owner, "timezone", "Europe/Amsterdam"),
            )

    co_owners = session.exec(
        select(CarCoOwner).where(CarCoOwner.car_id == booking.car_id, CarCoOwner.status == "accepted")
    ).all()
    for co in co_owners:
        co_user = session.get(User, co.user_id)
        if co_user:
            co_prefs = get_prefs(co_user)
            if co_prefs["booking_cancelled"]["push"]:
                create_notification(
                    session,
                    co_user.id,
                    f"{current_user.full_name} cancelled their booking for {car.name}",
                    booking.id,
                )
                background_tasks.add_task(send_web_push_task, co_user.id, f"{current_user.full_name} cancelled their booking for {car.name}")

    # Notify waitlist users whose requested period overlaps with the now-free slot
    waitlist_entries = session.exec(
        select(Waitlist).where(
            Waitlist.car_id == booking.car_id,
            Waitlist.start_datetime < booking.end_datetime,
            Waitlist.end_datetime > booking.start_datetime,
        )
    ).all()
    for entry in waitlist_entries:
        waitlist_user = session.get(User, entry.user_id)
        if waitlist_user:
            wl_prefs = get_prefs(waitlist_user)
            if wl_prefs["waitlist"]["push"]:
                create_notification(
                    session,
                    entry.user_id,
                    f"{car.name} may now be available for your requested dates",
                )
                background_tasks.add_task(send_web_push_task, entry.user_id, f"{car.name} may now be available for your requested dates")
            if wl_prefs["waitlist"]["email"]:
                background_tasks.add_task(
                    emailer.waitlist_availability_email,
                    to_email=waitlist_user.email,
                    full_name=waitlist_user.full_name,
                    car_name=car.name,
                    start_iso=entry.start_datetime.isoformat(),
                    end_iso=entry.end_datetime.isoformat(),
                    tz=getattr(waitlist_user, "timezone", "Europe/Amsterdam"),
                )

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
    if body.stops is not None:
        booking.stops_json = json.dumps(body.stops)
    if body.notes is not None:
        booking.notes = body.notes

    car = booking.car or session.get(Car, booking.car_id)
    if car is None:
        raise HTTPException(status_code=404, detail="Car not found")

    owner = car.owner or session.get(User, car.owner_id)
    session.add(booking)
    if owner:
        owner_prefs = get_prefs(owner)
        if owner_prefs["booking_reschedule"]["push"]:
            create_notification(
                session,
                owner.id,
                f"{current_user.full_name} rescheduled their booking for {car.name}",
                booking.id,
            )
            background_tasks.add_task(send_web_push_task, owner.id, f"{current_user.full_name} rescheduled their booking for {car.name}")
    session.commit()
    session.refresh(booking)

    if owner:
        owner_prefs = get_prefs(owner)
        if owner_prefs["booking_reschedule"]["email"] and owner.email:
            background_tasks.add_task(
                emailer.owner_booking_reschedule_email,
                owner_email=owner.email,
                owner_name=owner.full_name,
                car_name=car.name,
                borrower_name=current_user.full_name,
                start_iso=booking.start_datetime.isoformat(),
                end_iso=booking.end_datetime.isoformat(),
                booking_id=booking.id,
                tz=getattr(owner, "timezone", "Europe/Amsterdam"),
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


@router.get("/bookings/{booking_id}/detail", response_model=DashboardBookingRead)
def get_booking_detail(
    booking_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    booking = session.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")

    car = booking.car or session.get(Car, booking.car_id)
    if car is None:
        raise HTTPException(status_code=404, detail="Car not found")

    if booking.borrower_id != current_user.id and not is_car_manager(car.id, current_user.id, session):
        raise HTTPException(status_code=403, detail="Not allowed to view this booking")

    borrower = booking.borrower or session.get(User, booking.borrower_id)
    return DashboardBookingRead(
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
        stops=_parse_stops(booking.stops_json),
        notes=booking.notes,
        route_coordinates=_parse_coordinates(getattr(booking, "route_coordinates_json", None)),
    )


@router.get("/bookings/owner", response_model=List[DashboardBookingRead])
def list_owner_bookings(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if not current_user.role_owner:
        raise HTTPException(status_code=403, detail="Not an owner")

    managed_ids = get_managed_car_ids(current_user.id, session)
    if not managed_ids:
        return []
    bookings = session.exec(
        select(Booking)
        .join(Car)
        .where(Car.id.in_(managed_ids))
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
                stops=_parse_stops(booking.stops_json),
                notes=booking.notes,
            )
        )
    return result


@router.get("/bookings/borrower/stats", response_model=BorrowerStatsRead)
def get_borrower_stats(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    bookings = session.exec(
        select(Booking).where(
            Booking.borrower_id == current_user.id,
            Booking.status == BookingStatus.ACCEPTED.value,
        )
    ).all()

    def end_utc(b: Booking) -> datetime:
        return b.end_datetime if b.end_datetime.tzinfo else b.end_datetime.replace(tzinfo=timezone.utc)

    completed = [b for b in bookings if end_utc(b) < now]

    total_rides = len(completed)
    total_km = sum(b.total_km or 0 for b in completed)
    total_spent = sum(b.total_price or 0 for b in completed)

    # Favourite car: the one that appears most often
    car_counts: dict[int, tuple[str, int]] = {}
    for b in completed:
        car = b.car or session.get(Car, b.car_id)
        if car:
            prev = car_counts.get(car.id, (car.name, 0))
            car_counts[car.id] = (prev[0], prev[1] + 1)
    favourite_car = max(car_counts.values(), key=lambda x: x[1])[0] if car_counts else None

    return BorrowerStatsRead(
        total_rides=total_rides,
        total_km=round(total_km, 1),
        total_spent=round(total_spent, 2),
        favourite_car=favourite_car,
    )


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
                stops=_parse_stops(booking.stops_json),
                notes=booking.notes,
                created_at=getattr(booking, "created_at", None),
                last_reminder_sent=getattr(booking, "last_reminder_sent", None),
            )
        )
    return result


@router.post("/bookings/{booking_id}/remind")
def send_booking_reminder(
    booking_id: int,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    from datetime import datetime, timezone

    from models import CarCoOwner
    booking = session.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.borrower_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your booking")
    if booking.status != BookingStatus.PENDING.value:
        raise HTTPException(status_code=400, detail="Can only send reminders for pending bookings")

    now = datetime.now(timezone.utc)
    reference = getattr(booking, "last_reminder_sent", None) or getattr(booking, "created_at", None)
    if reference is not None:
        if reference.tzinfo is None:
            reference = reference.replace(tzinfo=timezone.utc)
        elapsed = (now - reference).total_seconds()
        if elapsed < 86400:
            hours_remaining = (86400 - elapsed) / 3600
            raise HTTPException(
                status_code=400,
                detail=f"You can send another reminder in {hours_remaining:.1f} hours",
            )

    car = booking.car or session.get(Car, booking.car_id)
    if car is None:
        raise HTTPException(status_code=404, detail="Car not found")

    reminder_message = f"{current_user.full_name} is waiting for your response on their booking for {car.name}"
    owner = session.get(User, car.owner_id)
    if owner:
        create_notification(session, owner.id, reminder_message, booking.id)
        background_tasks.add_task(send_web_push_task, owner.id, reminder_message)

    co_owners = session.exec(
        select(CarCoOwner).where(CarCoOwner.car_id == car.id, CarCoOwner.status == "accepted")
    ).all()
    for co in co_owners:
        co_user = session.get(User, co.user_id)
        if co_user:
            create_notification(session, co_user.id, reminder_message, booking.id)
            background_tasks.add_task(send_web_push_task, co_user.id, reminder_message)

    booking.last_reminder_sent = now
    session.add(booking)
    session.commit()
    session.refresh(booking)

    if owner:
        owner_prefs = get_prefs(owner)
        if owner_prefs["booking_reminder"]["email"] and owner.email:
            background_tasks.add_task(
                emailer.owner_booking_reminder_email,
                owner_email=owner.email,
                owner_name=owner.full_name,
                car_name=car.name,
                borrower_name=current_user.full_name,
                start_iso=booking.start_datetime.isoformat(),
                end_iso=booking.end_datetime.isoformat(),
                booking_id=booking.id,
                tz=getattr(owner, "timezone", "Europe/Amsterdam"),
            )

    return {"ok": True, "last_reminder_sent": booking.last_reminder_sent.isoformat()}


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
    if car is None or not is_car_manager(car.id, current_user.id, session):
        raise HTTPException(status_code=403, detail="Not allowed to modify this booking")
    if booking.status != BookingStatus.PENDING.value:
        raise HTTPException(status_code=400, detail="Only pending bookings can be accepted")

    booking.status = BookingStatus.ACCEPTED.value
    borrower = booking.borrower or session.get(User, booking.borrower_id)
    session.add(booking)
    if borrower:
        borrower_prefs = get_prefs(borrower)
        if borrower_prefs["booking_response"]["push"]:
            create_notification(
                session,
                borrower.id,
                f"Your booking for {car.name} was accepted",
                booking.id,
            )
            background_tasks.add_task(send_web_push_task, borrower.id, f"Your booking for {car.name} was accepted")
    session.commit()
    session.refresh(booking)

    if borrower:
        borrower_prefs = get_prefs(borrower)
        if borrower_prefs["booking_response"]["email"] and borrower.email:
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
                tz=getattr(borrower, "timezone", "Europe/Amsterdam"),
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
    if car is None or not is_car_manager(car.id, current_user.id, session):
        raise HTTPException(status_code=403, detail="Not allowed to modify this booking")
    if booking.status != BookingStatus.PENDING.value:
        raise HTTPException(status_code=400, detail="Only pending bookings can be declined")

    booking.status = BookingStatus.DECLINED.value
    borrower = booking.borrower or session.get(User, booking.borrower_id)
    session.add(booking)
    if borrower:
        borrower_prefs = get_prefs(borrower)
        if borrower_prefs["booking_response"]["push"]:
            create_notification(
                session,
                borrower.id,
                f"Your booking for {car.name} was declined",
                booking.id,
            )
            background_tasks.add_task(send_web_push_task, borrower.id, f"Your booking for {car.name} was declined")
    session.commit()
    session.refresh(booking)

    if borrower:
        borrower_prefs = get_prefs(borrower)
        if borrower_prefs["booking_response"]["email"] and borrower.email:
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
                tz=getattr(borrower, "timezone", "Europe/Amsterdam"),
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
    active_rentals: List[DashboardBookingRead] = []
    if current_user.role_owner:
        managed_ids = get_managed_car_ids(current_user.id, session)
        cars = session.exec(select(Car).where(Car.id.in_(managed_ids))).all() if managed_ids else []
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

        managed_ids_set = {c.id for c in cars}
        ongoing = session.exec(
            select(Booking)
            .join(Car)
            .where(
                Car.id.in_(managed_ids_set),
                Booking.status == BookingStatus.ACCEPTED.value,
                Booking.start_datetime <= now,
                Booking.end_datetime >= now,
            )
        ).all()
        for b in ongoing:
            car = getattr(b, "car", None) or session.get(Car, b.car_id)
            borrower = getattr(b, "borrower", None) or session.get(User, b.borrower_id)
            if not car:
                continue
            active_rentals.append(
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
                    borrower_name=borrower.full_name if borrower else None,
                    borrower_email=borrower.email if borrower else None,
                    stops=_parse_stops(b.stops_json),
                    notes=b.notes,
                )
            )

    return DashboardResponse(upcoming_bookings=upcoming_bookings, active_cars=active_cars, active_rentals=active_rentals)
