import secrets
from datetime import datetime, timedelta, timezone
from typing import List

import emailer
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from limiter import limiter
from sqlmodel import Session, select

from auth import (
    create_access_token,
    get_current_user,
    get_password_hash,
    get_session,
    user_to_read,
    verify_password,
)
from models import PasswordResetToken, User
from schemas import ChangePassword, LoginRequest, RequestPasswordReset, ResetPassword, TokenResponse, UserCreate, UserRead, UserUpdate

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
@limiter.limit("10/minute")
def login(
    request: Request,
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


@router.patch("/users/me", response_model=UserRead)
def update_me(
    data: UserUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if data.email is not None and data.email != current_user.email:
        existing = session.exec(select(User).where(User.email == data.email)).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use")
        current_user.email = data.email
    if data.full_name is not None:
        current_user.full_name = data.full_name
    if data.role_owner is not None:
        current_user.role_owner = data.role_owner
    if data.role_borrower is not None:
        current_user.role_borrower = data.role_borrower
    if data.timezone is not None:
        current_user.timezone = data.timezone
    if data.notification_prefs is not None:
        current_user.notification_prefs = data.notification_prefs
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return user_to_read(current_user)


@router.post("/users/me/change-password")
def change_password(
    data: ChangePassword,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters")
    current_user.password_hash = get_password_hash(data.new_password)
    session.add(current_user)
    session.commit()
    return {"ok": True}


@router.post("/auth/request-reset")
@limiter.limit("5/minute")
def request_password_reset(
    request: Request,
    data: RequestPasswordReset,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    user = session.exec(select(User).where(User.email == data.email)).first()
    if user:
        # Delete any existing tokens for this user
        existing = session.exec(
            select(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
        ).all()
        for t in existing:
            session.delete(t)

        token = secrets.token_urlsafe(32)
        reset_token = PasswordResetToken(
            user_id=user.id,
            token=token,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        session.add(reset_token)
        session.commit()

        reset_url = f"{emailer.APP_BASE_URL}/reset-password?token={token}"
        background_tasks.add_task(
            emailer.password_reset_email,
            to_email=user.email,
            full_name=user.full_name,
            reset_url=reset_url,
        )

    # Always return 200 to avoid email enumeration
    return {"ok": True}


@router.post("/auth/reset-password")
def reset_password(
    data: ResetPassword,
    session: Session = Depends(get_session),
):
    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    reset_token = session.exec(
        select(PasswordResetToken).where(PasswordResetToken.token == data.token)
    ).first()

    def _ensure_utc(dt: datetime) -> datetime:
        return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)

    if reset_token is None or _ensure_utc(reset_token.expires_at) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")

    user = session.get(User, reset_token.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user.password_hash = get_password_hash(data.new_password)
    session.add(user)
    session.delete(reset_token)
    session.commit()
    return {"ok": True}


@router.get("/admin/users", response_model=List[UserRead])
def list_all_users(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    users = session.exec(select(User).order_by(User.id)).all()
    return [user_to_read(u) for u in users]


@router.post("/admin/users/{user_id}/approve", response_model=UserRead)
def approve_user(
    user_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_approved = True
    session.add(user)
    session.commit()
    session.refresh(user)
    return user_to_read(user)


@router.delete("/admin/users/{user_id}")
def delete_user(
    user_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    session.delete(user)
    session.commit()
    return {"ok": True}
