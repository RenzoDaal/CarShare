import json
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlmodel import Session, select

import config
from auth import get_current_user, get_session
from models import Notification, PushSubscription, User
from schemas import NotificationRead

router = APIRouter()


def _send_web_push(session: Session, user_id: int, message: str) -> None:
    if not config.PUSH_ENABLED:
        logger.warning("Web push skipped: PUSH_ENABLED is False (check VAPID_PRIVATE_KEY and VAPID_PUBLIC_KEY)")
        return
    from pywebpush import WebPushException, webpush

    subs = session.exec(
        select(PushSubscription).where(PushSubscription.user_id == user_id)
    ).all()
    if not subs:
        logger.debug("Web push: no subscriptions found for user_id=%s", user_id)
        return

    # Count all unread notifications including the one just flushed above
    unread = session.exec(
        select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.is_read == False,  # noqa: E712
        )
    ).one()
    badge_count = unread or 1

    for sub in subs:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=json.dumps({"title": message, "badge": badge_count}),
                vapid_private_key=config.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": f"mailto:{config.VAPID_EMAIL}"},
                timeout=5,
            )
            logger.info("Web push sent to user_id=%s endpoint=%.60s", user_id, sub.endpoint)
        except WebPushException as ex:
            logger.error("WebPushException for user_id=%s: %s", user_id, ex)
            if ex.response is not None and ex.response.status_code == 410:
                logger.info("Removing expired push subscription for user_id=%s", user_id)
                session.delete(sub)
                session.commit()
        except Exception as ex:
            logger.error("Unexpected push error for user_id=%s: %s", user_id, ex)


def create_notification(
    session: Session,
    user_id: int,
    message: str,
    booking_id: Optional[int] = None,
):
    """Add a notification to the session (caller must commit) and send web push."""
    notif = Notification(user_id=user_id, message=message, booking_id=booking_id)
    session.add(notif)
    session.flush()  # ensure the new notification is visible to the count query below
    _send_web_push(session, user_id, message)


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


@router.delete("/notifications")
def clear_all_notifications(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    notifs = session.exec(
        select(Notification).where(Notification.user_id == current_user.id)
    ).all()
    for n in notifs:
        session.delete(n)
    session.commit()
    return {"ok": True}
