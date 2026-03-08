import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

import config
from auth import get_current_user, get_session
from models import PushSubscription, User

logger = logging.getLogger(__name__)

router = APIRouter()


class PushSubscribePayload(BaseModel):
    endpoint: str
    p256dh: str
    auth: str


@router.get("/push/vapid-public-key")
def get_vapid_public_key():
    return {"public_key": config.VAPID_PUBLIC_KEY}


@router.post("/push/subscribe")
def subscribe(
    payload: PushSubscribePayload,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    existing = session.exec(
        select(PushSubscription).where(PushSubscription.endpoint == payload.endpoint)
    ).first()
    if existing:
        existing.user_id = current_user.id
        existing.p256dh = payload.p256dh
        existing.auth = payload.auth
        session.add(existing)
    else:
        session.add(
            PushSubscription(
                user_id=current_user.id,
                endpoint=payload.endpoint,
                p256dh=payload.p256dh,
                auth=payload.auth,
            )
        )
    session.commit()
    return {"ok": True}


@router.get("/push/debug-key")
def debug_vapid_key(current_user: User = Depends(get_current_user)):
    """Show safe diagnostics about the VAPID private key (no secret content exposed)."""
    key = config.VAPID_PRIVATE_KEY
    return {
        "push_enabled": config.PUSH_ENABLED,
        "vapid_email": config.VAPID_EMAIL,
        "key_length": len(key),
        "key_starts_with": key[:30] if key else "(empty)",
        "key_ends_with": key[-20:] if key else "(empty)",
        "has_pem_header": "-----BEGIN" in key,
        "newline_count": key.count("\n"),
        "literal_backslash_n_count": key.count("\\n"),
    }


@router.post("/push/test")
def test_push(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Send a test push notification to the current user. Returns detail on success or failure."""
    if not config.PUSH_ENABLED:
        raise HTTPException(status_code=503, detail="PUSH_ENABLED is False — check VAPID keys in environment")

    from pywebpush import WebPushException, webpush
    import json

    subs = session.exec(
        select(PushSubscription).where(PushSubscription.user_id == current_user.id)
    ).all()
    if not subs:
        raise HTTPException(status_code=404, detail="No push subscriptions found for your account")

    results = []
    for sub in subs:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=json.dumps({"body": "Push notifications werken!"}),
                vapid_private_key=config.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": f"mailto:{config.VAPID_EMAIL}"},
                timeout=10,
            )
            logger.info("Test push sent to user_id=%s endpoint=%.60s", current_user.id, sub.endpoint)
            results.append({"endpoint": sub.endpoint[:40], "status": "sent"})
        except WebPushException as ex:
            status_code = ex.response.status_code if ex.response is not None else None
            body = ex.response.text if ex.response is not None else None
            logger.error("Test WebPushException user_id=%s status=%s body=%s", current_user.id, status_code, body)
            results.append({"endpoint": sub.endpoint[:40], "status": "error", "http_status": status_code, "detail": str(ex), "body": body})
        except Exception as ex:
            logger.error("Test push unexpected error user_id=%s: %s", current_user.id, ex)
            results.append({"endpoint": sub.endpoint[:40], "status": "error", "detail": str(ex)})

    return {"results": results}
