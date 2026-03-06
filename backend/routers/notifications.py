from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from auth import get_current_user, get_session
from models import Notification, User
from schemas import NotificationRead

router = APIRouter()


def create_notification(
    session: Session,
    user_id: int,
    message: str,
    booking_id: Optional[int] = None,
):
    """Add a notification to the session (caller must commit)."""
    notif = Notification(user_id=user_id, message=message, booking_id=booking_id)
    session.add(notif)


@router.get("/notifications", response_model=List[NotificationRead])
def list_notifications(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return session.exec(
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
    ).all()


@router.post("/notifications/read-all")
def mark_all_read(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    unread = session.exec(
        select(Notification).where(
            Notification.user_id == current_user.id,
            Notification.is_read == False,  # noqa: E712
        )
    ).all()
    for n in unread:
        n.is_read = True
        session.add(n)
    session.commit()
    return {"ok": True}


@router.patch("/notifications/{notification_id}/read")
def mark_read(
    notification_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    notif = session.get(Notification, notification_id)
    if notif and notif.user_id == current_user.id:
        notif.is_read = True
        session.add(notif)
        session.commit()
    return {"ok": True}
