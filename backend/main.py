import os
from calendar import monthrange
from datetime import date, datetime, timezone
from typing import List, Optional
from uuid import uuid4

import emailer
import schemas
from auth import (
    create_access_token,
    get_current_user,
    get_password_hash,
    get_session,
    user_to_read,
    verify_password,
)
from database import engine, init_db
from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from models import Booking, BookingStatus, Car, CarUnavailability, User
from routing import router as routing_router
from schemas import (
    CalendarDateRange,
    CarCreate,
    CarRead,
    CarUnavailabilityCreate,
    CarUnavailabilityRead,
    CarUpdate,
    DashboardBookingRead,
    DashboardResponse,
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserRead,
)
from sqlmodel import Session, select

app = FastAPI()

BASE_DATA_DIR = "data"
CAR_IMAGE_DIR = os.path.join(BASE_DATA_DIR, "car_images")
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB
os.makedirs(CAR_IMAGE_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=BASE_DATA_DIR), name="static")

_raw_origins = os.environ.get(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
)
origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routing_router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.post("/auth/register", response_model=UserRead)
def register_user(
    user_in: UserCreate,
    session: Session = Depends(get_session),
):
    existing = session.exec(select(User).where(User.email == user_in.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=user_in.email,
        password_hash=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role_owner=user_in.role_owner,
        role_borrower=user_in.role_borrower,
        is_approved=False,
    )

    session.add(user)
    session.commit()
    session.refresh(user)

    return user_to_read(user)


@app.post("/auth/login", response_model=TokenResponse)
def login(
    data: LoginRequest,
    session: Session = Depends(get_session),
):
    user = session.exec(select(User).where(User.email == data.email)).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    if not user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is awaiting approval from an administrator.",
        )

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user=user_to_read(user))


@app.get("/users/me", response_model=UserRead)
def read_me(current_user: User = Depends(get_current_user)):
    return user_to_read(current_user)


@app.post("/cars", response_model=CarRead, status_code=status.HTTP_201_CREATED)
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


@app.post("/cars/{car_id}/image", response_model=CarRead)
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

    # Delete old image file if one exists
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


@app.patch("/cars/{car_id}", response_model=CarRead)
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
        raise HTTPException(
            status_code=403,
            detail="Not allowed to update this car",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(car, field, value)

    session.add(car)
    session.commit()
    session.refresh(car)

    return car


def parse_iso(dt: str) -> datetime:
    # Handle trailing 'Z' from JS toISOString()
    if dt.endswith("Z"):
        dt = dt[:-1] + "+00:00"
    return datetime.fromisoformat(dt)


@app.get("/cars/available")
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
            Booking.start_datetime < end_dt,
            Booking.end_datetime > start_dt,
        )
    ).all()

    blocked_car_ids = {b.car_id for b in overlapping_bookings}

    # Also block cars with an owner unavailability block overlapping the requested dates
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


@app.get("/cars")
def list_cars(session: Session = Depends(get_session)):
    cars = session.exec(select(Car).where(Car.is_active == True)).all()
    return cars


@app.get("/cars/mine", response_model=list[CarRead])
def list_my_cars(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    cars = session.exec(select(Car).where(Car.owner_id == current_user.id)).all()
    return cars


@app.delete("/cars/{car_id}", status_code=status.HTTP_204_NO_CONTENT)
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

    # Delete unavailability blocks before deleting the car
    blocks = session.exec(
        select(CarUnavailability).where(CarUnavailability.car_id == car_id)
    ).all()
    for b in blocks:
        session.delete(b)

    session.delete(car)
    session.commit()


# --- Car unavailability (owner-managed blocked dates) ---

@app.get("/cars/{car_id}/unavailability", response_model=List[CarUnavailabilityRead])
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

    blocks = session.exec(
        select(CarUnavailability)
        .where(CarUnavailability.car_id == car_id)
        .order_by(CarUnavailability.start_date)
    ).all()
    return blocks


@app.post(
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
        raise HTTPException(
            status_code=400, detail="End date must be on or after start date"
        )

    block = CarUnavailability(
        car_id=car_id,
        start_date=data.start_date,
        end_date=data.end_date,
    )
    session.add(block)
    session.commit()
    session.refresh(block)
    return block


@app.delete(
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


# --- Car calendar (borrower view — combines bookings + owner blocks) ---

@app.get("/cars/{car_id}/calendar", response_model=List[CalendarDateRange])
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

    ranges: List[CalendarDateRange] = []

    # Accepted bookings overlapping this month
    month_start_dt = datetime(year, month, 1, 0, 0, 0)
    month_end_dt = datetime(year, month, days_in_month, 23, 59, 59)
    bookings = session.exec(
        select(Booking).where(
            Booking.car_id == car_id,
            Booking.status == BookingStatus.ACCEPTED.value,
            Booking.start_datetime <= month_end_dt,
            Booking.end_datetime >= month_start_dt,
        )
    ).all()
    for b in bookings:
        ranges.append(
            CalendarDateRange(
                start=b.start_datetime.date(),
                end=b.end_datetime.date(),
            )
        )

    # Owner unavailability blocks overlapping this month
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


@app.post("/bookings")
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

    start_dt = datetime.fromisoformat(start_datetime)
    end_dt = datetime.fromisoformat(end_datetime)

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

    return booking


@app.post("/bookings/{booking_id}/cancel", response_model=schemas.BookingRead)
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

    booking.status = BookingStatus.CANCELLED.value
    session.add(booking)
    session.commit()
    session.refresh(booking)

    return schemas.BookingRead(
        id=booking.id,
        car=schemas.CarRead(
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


@app.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    now = datetime.now(timezone.utc)

    bookings_stmt = (
        select(Booking)
        .where(
            Booking.borrower_id == current_user.id,
            Booking.end_datetime >= now,
            Booking.status != BookingStatus.CANCELLED.value,
            Booking.status != BookingStatus.DECLINED.value,
        )
        .order_by(Booking.start_datetime)
    )
    bookings: List[Booking] = session.exec(bookings_stmt).all()

    upcoming_bookings: list[dict] = []

    for b in bookings:
        car = getattr(b, "car", None) or session.get(Car, b.car_id)
        if not car:
            continue

        upcoming_bookings.append(
            {
                "id": b.id,
                "car": {
                    "id": car.id,
                    "owner_id": car.owner_id,
                    "name": car.name,
                    "description": car.description,
                    "price_per_km": car.price_per_km,
                    "is_active": car.is_active,
                    "image_url": getattr(car, "image_url", None),
                },
                "start_datetime": b.start_datetime,
                "end_datetime": b.end_datetime,
                "status": str(getattr(b, "status", "")),
                "total_price": getattr(b, "total_price", None),
            }
        )

    active_cars: list[dict] = []

    if current_user.role_owner:
        cars_stmt = select(Car).where(Car.owner_id == current_user.id)
        cars: List[Car] = session.exec(cars_stmt).all()

        for car in cars:
            active_cars.append(
                {
                    "id": car.id,
                    "owner_id": car.owner_id,
                    "name": car.name,
                    "description": car.description,
                    "price_per_km": car.price_per_km,
                    "is_active": car.is_active,
                    "image_url": getattr(car, "image_url", None),
                }
            )

    return {
        "upcoming_bookings": upcoming_bookings,
        "active_cars": active_cars,
    }


@app.get("/bookings/owner", response_model=List[schemas.DashboardBookingRead])
def list_owner_bookings(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if not current_user.role_owner:
        raise HTTPException(status_code=403, detail="Not an owner")

    statement = (
        select(Booking)
        .join(Car)
        .where(Car.owner_id == current_user.id)
        .order_by(Booking.start_datetime.desc())
    )
    bookings = session.exec(statement).all()

    result: List[schemas.DashboardBookingRead] = []
    for booking in bookings:
        car = booking.car
        if car is None:
            continue

        result.append(
            schemas.DashboardBookingRead(
                id=booking.id,
                car=schemas.CarRead(
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


@app.get("/bookings/borrower", response_model=List[schemas.DashboardBookingRead])
def list_borrower_bookings(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if not current_user.role_borrower:
        raise HTTPException(status_code=403, detail="Not a borrower")

    statement = (
        select(Booking)
        .where(Booking.borrower_id == current_user.id)
        .order_by(Booking.start_datetime.desc())
    )
    bookings = session.exec(statement).all()

    result: List[schemas.DashboardBookingRead] = []
    for booking in bookings:
        car = booking.car
        if car is None:
            continue

        result.append(
            schemas.DashboardBookingRead(
                id=booking.id,
                car=schemas.CarRead(
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


@app.post("/bookings/{booking_id}/accept", response_model=schemas.BookingRead)
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
        raise HTTPException(
            status_code=403, detail="Not allowed to modify this booking"
        )

    if booking.status != BookingStatus.PENDING.value:
        raise HTTPException(
            status_code=400, detail="Only pending bookings can be accepted"
        )

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
        car=schemas.CarRead(
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


@app.post("/bookings/{booking_id}/decline", response_model=schemas.BookingRead)
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
        raise HTTPException(
            status_code=403, detail="Not allowed to modify this booking"
        )

    if booking.status != BookingStatus.PENDING.value:
        raise HTTPException(
            status_code=400, detail="Only pending bookings can be declined"
        )

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
        car=schemas.CarRead(
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


@app.get("/health")
def health():
    return {"status": "ok"}
