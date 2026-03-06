from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from auth import (
    create_access_token,
    get_current_user,
    get_password_hash,
    get_session,
    user_to_read,
    verify_password,
)
from models import User
from schemas import LoginRequest, TokenResponse, UserCreate, UserRead

router = APIRouter()


@router.post("/auth/register", response_model=UserRead)
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


@router.post("/auth/login", response_model=TokenResponse)
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


@router.get("/users/me", response_model=UserRead)
def read_me(current_user: User = Depends(get_current_user)):
    return user_to_read(current_user)
