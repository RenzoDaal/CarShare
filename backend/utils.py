import json
from datetime import datetime

DEFAULT_PREFS: dict = {
    "booking_request": {"push": True, "email": True},
    "booking_response": {"push": True, "email": True},
    "booking_reschedule": {"push": True, "email": True},
    "booking_cancelled": {"push": True, "email": True},
    "waitlist": {"push": True, "email": True},
}


def get_prefs(user) -> dict:
    """Return the user's notification preferences, filling in defaults for any missing keys."""
    raw = getattr(user, "notification_prefs", None)
    if not raw:
        return {k: dict(v) for k, v in DEFAULT_PREFS.items()}
    try:
        stored = json.loads(raw)
        return {
            key: {
                "push": stored.get(key, {}).get("push", True),
                "email": stored.get(key, {}).get("email", True),
            }
            for key in DEFAULT_PREFS
        }
    except Exception:
        return {k: dict(v) for k, v in DEFAULT_PREFS.items()}


def parse_iso(dt: str) -> datetime:
    """Parse an ISO datetime string, handling the trailing 'Z' from JS toISOString()."""
    if dt.endswith("Z"):
        dt = dt[:-1] + "+00:00"
    return datetime.fromisoformat(dt)


def get_managed_car_ids(user_id: int, session) -> set:
    """Return IDs of all cars the user can manage (primary owner or accepted co-owner)."""
    from models import Car, CarCoOwner
    from sqlmodel import select
    primary = session.exec(select(Car.id).where(Car.owner_id == user_id)).all()
    co_owned = session.exec(
        select(CarCoOwner.car_id).where(
            CarCoOwner.user_id == user_id,
            CarCoOwner.status == "accepted",
        )
    ).all()
    return set(primary) | set(co_owned)


def is_car_manager(car_id: int, user_id: int, session) -> bool:
    """Check if user is primary owner or accepted co-owner of the car."""
    from models import Car, CarCoOwner
    from sqlmodel import select
    car = session.get(Car, car_id)
    if car is None:
        return False
    if car.owner_id == user_id:
        return True
    co_owner = session.exec(
        select(CarCoOwner).where(
            CarCoOwner.car_id == car_id,
            CarCoOwner.user_id == user_id,
            CarCoOwner.status == "accepted",
        )
    ).first()
    return co_owner is not None
