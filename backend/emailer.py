import os
import smtplib
from datetime import datetime
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


def _format_dt(iso: str) -> str:
    """Format a naive UTC ISO datetime string for display in emails."""
    dt = datetime.fromisoformat(iso)
    return dt.strftime("%d %B %Y at %H:%M UTC")


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


def password_reset_email(
    *,
    to_email: str,
    full_name: str,
    reset_url: str,
) -> None:
    subject = "Reset your CarShare password"
    body = (
        f"Hi {full_name},\n\n"
        f"Someone requested a password reset for your CarShare account.\n\n"
        f"Click the link below to set a new password (valid for 1 hour):\n"
        f"{reset_url}\n\n"
        f"If you did not request this, you can safely ignore this email.\n"
    )
    send_email(to_email, subject, body)


def owner_booking_request_email(
    *,
    owner_email: str,
    owner_name: str,
    car_name: str,
    borrower_name: str,
    start_iso: str,
    end_iso: str,
    booking_id: int,
    notes: Optional[str] = None,
) -> None:
    subject = f"New booking request for {car_name}"
    notes_line = f"Note from borrower: {notes}\n" if notes else ""
    body = (
        f"Hi {owner_name},\n\n"
        f"{borrower_name} requested to book your car: {car_name}.\n\n"
        f"Start: {_format_dt(start_iso)}\n"
        f"End:   {_format_dt(end_iso)}\n"
        f"{notes_line}"
        f"Booking ID: {booking_id}\n\n"
        f"Respond here: {APP_BASE_URL}/ownerappointments\n"
    )
    send_email(owner_email, subject, body)


def borrower_booking_confirmation_email(
    *,
    borrower_email: str,
    borrower_name: str,
    car_name: str,
    owner_name: str,
    start_iso: str,
    end_iso: str,
    booking_id: int,
) -> None:
    subject = f"Booking request sent: {car_name}"
    body = (
        f"Hi {borrower_name},\n\n"
        f"Your booking request for {car_name} has been sent to {owner_name}.\n\n"
        f"Start: {_format_dt(start_iso)}\n"
        f"End:   {_format_dt(end_iso)}\n"
        f"Booking ID: {booking_id}\n\n"
        f"You will receive an email once the owner responds.\n"
        f"View your bookings: {APP_BASE_URL}/borrowerappointments\n"
    )
    send_email(borrower_email, subject, body)


def owner_booking_reschedule_email(
    *,
    owner_email: str,
    owner_name: str,
    car_name: str,
    borrower_name: str,
    start_iso: str,
    end_iso: str,
    booking_id: int,
) -> None:
    subject = f"Booking rescheduled: {car_name}"
    body = (
        f"Hi {owner_name},\n\n"
        f"{borrower_name} has rescheduled their booking for {car_name}.\n\n"
        f"New start: {_format_dt(start_iso)}\n"
        f"New end:   {_format_dt(end_iso)}\n"
        f"Booking ID: {booking_id}\n\n"
        f"The booking is now pending your approval again.\n"
        f"Respond here: {APP_BASE_URL}/ownerappointments\n"
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
    status: str,
) -> None:
    subject = f"Your booking was {status}: {car_name}"
    body = (
        f"Hi {borrower_name},\n\n"
        f"{owner_name} has {status} your booking request for: {car_name}.\n\n"
        f"Start: {_format_dt(start_iso)}\n"
        f"End:   {_format_dt(end_iso)}\n"
        f"Booking ID: {booking_id}\n\n"
        f"View your bookings: {APP_BASE_URL}/borrowerappointments\n"
    )
    send_email(borrower_email, subject, body)


def waitlist_availability_email(
    *,
    to_email: str,
    full_name: str,
    car_name: str,
    start_iso: str,
    end_iso: str,
) -> None:
    subject = f"{car_name} may now be available"
    body = (
        f"Hi {full_name},\n\n"
        f"Good news! A booking for {car_name} was cancelled, and it may now be available "
        f"for your requested dates:\n\n"
        f"Start: {_format_dt(start_iso)}\n"
        f"End:   {_format_dt(end_iso)}\n\n"
        f"Book it before someone else does: {APP_BASE_URL}/reserve\n"
    )
    send_email(to_email, subject, body)
