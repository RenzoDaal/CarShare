from auth import (
    create_access_token,
    get_current_user,
    get_password_hash,
    get_session,
    user_to_read,
    verify_password,
)
from database import engine, init_db
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import Booking, BookingStatus, Car, User
from schemas import LoginRequest, TokenResponse, UserCreate, UserRead
from sqlmodel import Session, select

app = FastAPI()

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


@app.get("/cars")
def list_cars(session: Session = Depends(get_session)):
    cars = session.exec(select(Car).where(Car.is_active == True)).all()
    return cars


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
