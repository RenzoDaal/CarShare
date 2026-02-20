import os
import smtplib
from email.message import EmailMessage
from typing import Optional


def _env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


EMAIL_ENABLED = _env_bool("EMAIL_ENABLED", False)

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "CarShare <no-reply@localhost>")
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:5173")


def send_email(to_email: str, subject: str, body_text: str) -> None:
    """
    Sends a plain-text email via SMTP (STARTTLS).
    Safe to call from FastAPI BackgroundTasks.
    """
    if not EMAIL_ENABLED:
        return

    if not (SMTP_HOST and SMTP_PORT and SMTP_FROM):
        # Misconfigured; fail silently to avoid breaking bookings
        return

    msg = EmailMessage()
    msg["From"] = SMTP_FROM
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body_text)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        if SMTP_USER:
            server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)


def owner_booking_request_email(
    *,
    owner_email: str,
    owner_name: str,
    car_name: str,
    borrower_name: str,
    start_iso: str,
    end_iso: str,
    booking_id: int,
) -> None:
    subject = f"New booking request for {car_name}"
    body = (
        f"Hi {owner_name},\n\n"
        f"{borrower_name} requested to book your car: {car_name}.\n\n"
        f"Start: {start_iso}\n"
        f"End:   {end_iso}\n"
        f"Booking ID: {booking_id}\n\n"
        f"Respond here: {APP_BASE_URL}/owner/appointments\n"
    )
    send_email(owner_email, subject, body)


def borrower_booking_response_email(
    *,
    borrower_email: str,
    borrower_name: str,
    car_name: str,
    owner_name: str,
    start_iso: str,
    end_iso: str,
    booking_id: int,
    status: str,  # accepted/declined
) -> None:
    subject = f"Your booking was {status}: {car_name}"
    body = (
        f"Hi {borrower_name},\n\n"
        f"{owner_name} has {status} your booking request for: {car_name}.\n\n"
        f"Start: {start_iso}\n"
        f"End:   {end_iso}\n"
        f"Booking ID: {booking_id}\n\n"
        f"View your bookings: {APP_BASE_URL}/borrower/appointments\n"
    )
    send_email(borrower_email, subject, body)
