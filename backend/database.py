import os

from sqlalchemy import text
from sqlmodel import SQLModel, create_engine

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DB_DIR, exist_ok=True)

DATABASE_URL = f"sqlite:///{os.path.join(DB_DIR, 'carshare.db')}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)


def init_db():
    SQLModel.metadata.create_all(engine)
    _run_migrations()


def _run_migrations():
    migrations = [
        "ALTER TABLE user ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0",
        "ALTER TABLE booking ADD COLUMN stops_json TEXT",
        "ALTER TABLE booking ADD COLUMN notes TEXT",
        "ALTER TABLE user ADD COLUMN timezone TEXT NOT NULL DEFAULT 'Europe/Amsterdam'",
        "ALTER TABLE user ADD COLUMN notification_prefs TEXT",
        "ALTER TABLE booking ADD COLUMN created_at TEXT",
        "ALTER TABLE booking ADD COLUMN last_reminder_sent TEXT",
        "ALTER TABLE car ADD COLUMN price_mode TEXT NOT NULL DEFAULT 'manual'",
        "ALTER TABLE car ADD COLUMN fuel_type TEXT",
        "ALTER TABLE car ADD COLUMN calc_battery_kwh REAL",
        "ALTER TABLE car ADD COLUMN calc_range_km REAL",
        "ALTER TABLE car ADD COLUMN calc_charge_cost_per_kwh REAL",
        "ALTER TABLE car ADD COLUMN calc_consumption_per_100km REAL",
        "ALTER TABLE car ADD COLUMN calc_fuel_price_per_liter REAL",
        "ALTER TABLE booking ADD COLUMN route_coordinates_json TEXT",
    ]
    with engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                pass  # Column already exists
