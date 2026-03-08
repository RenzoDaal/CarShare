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
