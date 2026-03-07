import os

from database import init_db
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routing import router as routing_router
from routers.bookings import router as bookings_router
from routers.cars import router as cars_router
from routers.notifications import router as notifications_router
from routers.users import router as users_router
from routers.waitlist import router as waitlist_router

app = FastAPI()

app.mount("/static", StaticFiles(directory="data"), name="static")

_raw_origins = os.environ.get(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
)
origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users_router)
app.include_router(cars_router)
app.include_router(bookings_router)
app.include_router(notifications_router)
app.include_router(waitlist_router)
app.include_router(routing_router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}
