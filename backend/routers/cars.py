import os
from calendar import monthrange
from datetime import date, datetime
from typing import List
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlmodel import Session, select

from auth import get_current_user, get_session
from config import BASE_DATA_DIR, CAR_IMAGE_DIR, MAX_IMAGE_SIZE
from models import Booking, BookingStatus, Car, CarImage, CarUnavailability, User
from schemas import (
    CalendarDateRange,
    CarCreate,
    CarImageRead,
    CarRead,
    CarStatsRead,
    CarUnavailabilityCreate,
    CarUnavailabilityRead,
    CarUpdate,
)
from utils import parse_iso

router = APIRouter()


@router.get("/cars/stats", response_model=List[CarStatsRead])
def get_car_stats(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if not current_user.role_owner:
        raise HTTPException(status_code=403, detail="Not an owner")
    cars = session.exec(select(Car).where(Car.owner_id == current_user.id)).all()
    result = []
    for car in cars:
        accepted_bookings = session.exec(
            select(Booking).where(
                Booking.car_id == car.id,
                Booking.status == BookingStatus.ACCEPTED.value,
            )
        ).all()
        result.append(
            CarStatsRead(
                car_id=car.id,
                car_name=car.name,
                total_bookings=len(accepted_bookings),
                total_km=sum(b.total_km or 0 for b in accepted_bookings),
                total_earnings=sum(b.total_price or 0 for b in accepted_bookings),
            )
        )
    return result


@router.post("/cars", response_model=CarRead, status_code=status.HTTP_201_CREATED)
def create_car(
    data: CarCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    car = Car(
        owner_id=current_user.id,
        name=data.name,
        description=data.description,
        price_per_km=data.price_per_km,
        is_active=True,
    )
    session.add(car)
    session.commit()
    session.refresh(car)
    return car


@router.post("/cars/{car_id}/image", response_model=CarRead)
async def upload_car_image(
    car_id: int,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    car = session.get(Car, car_id)
    if car is None:
        raise HTTPException(status_code=404, detail="Car not found")
    if car.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed to update this car")

    _, ext = os.path.splitext(file.filename or "")
    ext = ext.lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        raise HTTPException(status_code=400, detail="Unsupported image type")

    contents = await file.read()
    if len(contents) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="Image file too large (max 5 MB)")

    if car.image_url:
        old_path = os.path.join(BASE_DATA_DIR, car.image_url[len("/static/"):])
        if os.path.isfile(old_path):
            os.remove(old_path)

    filename = f"{car_id}_{uuid4().hex}{ext}"
    filepath = os.path.join(CAR_IMAGE_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(contents)

    car.image_url = f"/static/car_images/{filename}"
    session.add(car)
    session.commit()
    session.refresh(car)
    return car


@router.patch("/cars/{car_id}", response_model=CarRead)
def update_car(
    car_id: int,
    data: CarUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    car = session.get(Car, car_id)
    if car is None:
        raise HTTPException(status_code=404, detail="Car not found")
    if car.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed to update this car")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(car, field, value)

    session.add(car)
    session.commit()
    session.refresh(car)
    return car


@router.get("/cars/available")
def list_available_cars(
    start_datetime: str,
    end_datetime: str,
    session: Session = Depends(get_session),
):
    try:
        start_dt = parse_iso(start_datetime)
        end_dt = parse_iso(end_datetime)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid datetime format")

    if end_dt <= start_dt:
        raise HTTPException(
            status_code=400,
            detail="End datetime must be after start datetime",
        )

    overlapping_bookings = session.exec(
        select(Booking).where(
            Booking.status != BookingStatus.PENDING.value,
            Booking.status != BookingStatus.DECLINED.value,
            Booking.status != BookingStatus.CANCELLED.value,
            Booking.start_datetime < end_dt,
            Booking.end_datetime > start_dt,
        )
    ).all()
    blocked_car_ids = {b.car_id for b in overlapping_bookings}

    start_date = start_dt.date()
    end_date = end_dt.date()
    unavailability_blocks = session.exec(
        select(CarUnavailability).where(
            CarUnavailability.start_date <= end_date,
            CarUnavailability.end_date >= start_date,
        )
    ).all()
    blocked_car_ids |= {b.car_id for b in unavailability_blocks}

    cars = session.exec(select(Car).where(Car.is_active == True)).all()
    if blocked_car_ids:
        cars = [c for c in cars if c.id not in blocked_car_ids]

    return cars


@router.get("/cars/mine", response_model=List[CarRead])
def list_my_cars(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return session.exec(select(Car).where(Car.owner_id == current_user.id)).all()


@router.get("/cars")
def list_cars(session: Session = Depends(get_session)):
    return session.exec(select(Car).where(Car.is_active == True)).all()


@router.delete("/cars/{car_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_car(
    car_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    car = session.get(Car, car_id)
    if car is None:
        raise HTTPException(status_code=404, detail="Car not found")
    if car.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed to delete this car")

    if car.image_url:
        image_path = os.path.join(BASE_DATA_DIR, car.image_url[len("/static/"):])
        if os.path.isfile(image_path):
            os.remove(image_path)

    blocks = session.exec(
        select(CarUnavailability).where(CarUnavailability.car_id == car_id)
    ).all()
    for b in blocks:
        session.delete(b)

    session.delete(car)
    session.commit()


# --- Gallery images ---

@router.get("/cars/{car_id}/images", response_model=List[CarImageRead])
def list_car_images(
    car_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return session.exec(
        select(CarImage).where(CarImage.car_id == car_id).order_by(CarImage.order)
    ).all()


@router.post("/cars/{car_id}/images", response_model=CarImageRead, status_code=status.HTTP_201_CREATED)
async def add_car_image(
    car_id: int,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    car = session.get(Car, car_id)
    if car is None:
        raise HTTPException(status_code=404, detail="Car not found")
    if car.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed to update this car")

    _, ext = os.path.splitext(file.filename or "")
    ext = ext.lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        raise HTTPException(status_code=400, detail="Unsupported image type")

    contents = await file.read()
    if len(contents) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="Image file too large (max 5 MB)")

    existing = session.exec(select(CarImage).where(CarImage.car_id == car_id)).all()
    order = len(existing)

    filename = f"{car_id}_{uuid4().hex}{ext}"
    filepath = os.path.join(CAR_IMAGE_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(contents)

    url = f"/static/car_images/{filename}"
    image = CarImage(car_id=car_id, url=url, order=order)
    session.add(image)

    # Keep car.image_url in sync with the first gallery image
    if not car.image_url or order == 0:
        car.image_url = url
        session.add(car)

    session.commit()
    session.refresh(image)
    return image


@router.delete("/cars/{car_id}/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_car_image(
    car_id: int,
    image_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    car = session.get(Car, car_id)
    if car is None:
        raise HTTPException(status_code=404, detail="Car not found")
    if car.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed to update this car")

    image = session.get(CarImage, image_id)
    if image is None or image.car_id != car_id:
        raise HTTPException(status_code=404, detail="Image not found")

    file_path = os.path.join(BASE_DATA_DIR, image.url[len("/static/"):])
    if os.path.isfile(file_path):
        os.remove(file_path)

    session.delete(image)

    # Re-assign car.image_url to the next remaining image
    remaining = session.exec(
        select(CarImage).where(CarImage.car_id == car_id).order_by(CarImage.order)
    ).all()
    car.image_url = remaining[0].url if remaining else None
    session.add(car)
    session.commit()


# --- Unavailability (owner-managed blocked dates) ---

@router.get("/cars/{car_id}/unavailability", response_model=List[CarUnavailabilityRead])
def list_car_unavailability(
    car_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    car = session.get(Car, car_id)
    if car is None:
        raise HTTPException(status_code=404, detail="Car not found")
    if car.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed to view this car's unavailability")

    return session.exec(
        select(CarUnavailability)
        .where(CarUnavailability.car_id == car_id)
        .order_by(CarUnavailability.start_date)
    ).all()


@router.post(
    "/cars/{car_id}/unavailability",
    response_model=CarUnavailabilityRead,
    status_code=status.HTTP_201_CREATED,
)
def add_car_unavailability(
    car_id: int,
    data: CarUnavailabilityCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    car = session.get(Car, car_id)
    if car is None:
        raise HTTPException(status_code=404, detail="Car not found")
    if car.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed to update this car")
    if data.end_date < data.start_date:
        raise HTTPException(status_code=400, detail="End date must be on or after start date")

    block = CarUnavailability(car_id=car_id, start_date=data.start_date, end_date=data.end_date)
    session.add(block)
    session.commit()
    session.refresh(block)
    return block


@router.delete(
    "/cars/{car_id}/unavailability/{block_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_car_unavailability(
    car_id: int,
    block_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    car = session.get(Car, car_id)
    if car is None:
        raise HTTPException(status_code=404, detail="Car not found")
    if car.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed to update this car")

    block = session.get(CarUnavailability, block_id)
    if block is None or block.car_id != car_id:
        raise HTTPException(status_code=404, detail="Unavailability block not found")

    session.delete(block)
    session.commit()


# --- Calendar (borrower view) ---

@router.get("/cars/{car_id}/calendar", response_model=List[CalendarDateRange])
def get_car_calendar(
    car_id: int,
    year: int,
    month: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    car = session.get(Car, car_id)
    if car is None:
        raise HTTPException(status_code=404, detail="Car not found")

    _, days_in_month = monthrange(year, month)
    month_start = date(year, month, 1)
    month_end = date(year, month, days_in_month)
    month_start_dt = datetime(year, month, 1, 0, 0, 0)
    month_end_dt = datetime(year, month, days_in_month, 23, 59, 59)

    ranges: List[CalendarDateRange] = []

    bookings = session.exec(
        select(Booking).where(
            Booking.car_id == car_id,
            Booking.status == BookingStatus.ACCEPTED.value,
            Booking.start_datetime <= month_end_dt,
            Booking.end_datetime >= month_start_dt,
        )
    ).all()
    for b in bookings:
        ranges.append(CalendarDateRange(start=b.start_datetime.date(), end=b.end_datetime.date()))

    blocks = session.exec(
        select(CarUnavailability).where(
            CarUnavailability.car_id == car_id,
            CarUnavailability.start_date <= month_end,
            CarUnavailability.end_date >= month_start,
        )
    ).all()
    for b in blocks:
        ranges.append(CalendarDateRange(start=b.start_date, end=b.end_date))

    return ranges
