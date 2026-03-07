from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from auth import get_current_user, get_session
from models import Car, User, Waitlist
from schemas import WaitlistCreate, WaitlistRead
from utils import parse_iso

router = APIRouter()


@router.post("/waitlist", response_model=WaitlistRead, status_code=status.HTTP_201_CREATED)
def join_waitlist(
    data: WaitlistCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    car = session.get(Car, data.car_id)
    if car is None:
        raise HTTPException(status_code=404, detail="Car not found")

    start_dt = parse_iso(data.start_datetime)
    end_dt = parse_iso(data.end_datetime)
    if end_dt <= start_dt:
        raise HTTPException(status_code=400, detail="End time must be after start time")

    # Prevent duplicate entries for the same car and overlapping dates
    existing = session.exec(
        select(Waitlist).where(
            Waitlist.car_id == data.car_id,
            Waitlist.user_id == current_user.id,
        )
    ).all()
    for e in existing:
        if e.start_datetime < end_dt and e.end_datetime > start_dt:
            raise HTTPException(status_code=400, detail="You are already on the waitlist for this car and period")

    entry = Waitlist(
        car_id=data.car_id,
        user_id=current_user.id,
        start_datetime=start_dt,
        end_datetime=end_dt,
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)

    return WaitlistRead(
        id=entry.id,
        car_id=entry.car_id,
        car_name=car.name,
        start_datetime=entry.start_datetime,
        end_datetime=entry.end_datetime,
        created_at=entry.created_at,
    )


@router.get("/waitlist/mine", response_model=List[WaitlistRead])
def list_my_waitlist(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    entries = session.exec(
        select(Waitlist)
        .where(Waitlist.user_id == current_user.id)
        .order_by(Waitlist.start_datetime)
    ).all()

    result = []
    for e in entries:
        car = session.get(Car, e.car_id)
        result.append(WaitlistRead(
            id=e.id,
            car_id=e.car_id,
            car_name=car.name if car else "Unknown",
            start_datetime=e.start_datetime,
            end_datetime=e.end_datetime,
            created_at=e.created_at,
        ))
    return result


@router.delete("/waitlist/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def leave_waitlist(
    entry_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    entry = session.get(Waitlist, entry_id)
    if entry is None or entry.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Waitlist entry not found")
    session.delete(entry)
    session.commit()
