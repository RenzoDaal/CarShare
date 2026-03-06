from datetime import datetime


def parse_iso(dt: str) -> datetime:
    """Parse an ISO datetime string, handling the trailing 'Z' from JS toISOString()."""
    if dt.endswith("Z"):
        dt = dt[:-1] + "+00:00"
    return datetime.fromisoformat(dt)
