import os

BASE_DATA_DIR = "data"
CAR_IMAGE_DIR = os.path.join(BASE_DATA_DIR, "car_images")
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB
os.makedirs(CAR_IMAGE_DIR, exist_ok=True)
