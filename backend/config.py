import os

BASE_DATA_DIR = "data"
CAR_IMAGE_DIR = os.path.join(BASE_DATA_DIR, "car_images")
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB
os.makedirs(CAR_IMAGE_DIR, exist_ok=True)

# VAPID private key: raw URL-safe base64 (no PEM headers, no newlines needed)
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
VAPID_EMAIL = os.environ.get("VAPID_EMAIL", "carshareservices@gmail.com")
PUSH_ENABLED = bool(VAPID_PRIVATE_KEY and VAPID_PUBLIC_KEY)
