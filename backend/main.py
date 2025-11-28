import os
from datetime import datetime
from uuid import uuid4

from auth import (
    create_access_token,
    get_current_user,
    get_password_hash,
    get_session,
    user_to_read,
    verify_password,
)
from database import engine, init_db
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from models import Booking, BookingStatus, Car, User
from schemas import (
    CarCreate,
    CarRead,
    CarUpdate,
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserRead,
)
from sqlmodel import Session, select

app = FastAPI()

BASE_DATA_DIR = "data"
CAR_IMAGE_DIR = os.path.join(BASE_DATA_DIR, "car_images")
os.makedirs(CAR_IMAGE_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=BASE_DATA_DIR), name="static")

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://10.142.1.159:5173",
    "http://10.142.1.159:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user=user_to_read(user))


@app.get("/users/me", response_model=UserRead)
def read_me(current_user: User = Depends(get_current_user)):
    return user_to_read(current_user)


def get_session():
    with Session(engine) as session:
        yield session


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
    request: Request = None,
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

    filename = f"{car_id}_{uuid4().hex}{ext}"
    filepath = os.path.join(CAR_IMAGE_DIR, filename)

    contents = await file.read()
    with open(filepath, "wb") as f:
        f.write(contents)

    base_url = str(request.base_url).rstrip("/") if request else ""
    car.image_url = f"{base_url}/static/car_images/{filename}"

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

    update_data = data.dict(exclude_unset=True)
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
            Booking.status != BookingStatus.CANCELLED,
            Booking.start_datetime < end_dt,
            Booking.end_datetime > start_dt,
        )
    ).all()

    blocked_car_ids = {b.car_id for b in overlapping_bookings}

    cars = session.exec(select(Car).where(Car.is_active == True)).all()

    if blocked_car_ids:
        cars = [c for c in cars if c.id not in blocked_car_ids]

    return cars


@app.get("/cars")
def list_cars(session: Session = Depends(get_session)):
    cars = session.exec(select(Car).where(Car.is_active == True)).all()
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

    session.delete(car)
    session.commit()


@app.get("/bookings")
def list_bookings(session: Session = Depends(get_session)):
    bookings = session.exec(select(Booking)).all()
    return bookings


@app.post("/bookings")
def create_booking(
    borrower_id: int,
    car_id: int,
    start_datetime: str,
    end_datetime: str,
    session: Session = Depends(get_session),
):
    from datetime import datetime

    car = session.get(Car, car_id)
    borrower = session.get(User, borrower_id)

    if car is None:
        raise HTTPException(status_code=404, detail="Car not found")
    if borrower is None:
        raise HTTPException(status_code=404, detail="User not found")

    start_dt = datetime.fromisoformat(start_datetime)
    end_dt = datetime.fromisoformat(end_datetime)

    booking = Booking(
        car_id=car.id,
        borrower_id=borrower.id,
        start_datetime=start_dt,
        end_datetime=end_dt,
        price_per_km=car.price_per_km,
        status=BookingStatus.PENDING,
    )

    session.add(booking)
    session.commit()
    session.refresh(booking)

    return booking


@app.get("/health")
def health():
    return {"status": "ok"}
