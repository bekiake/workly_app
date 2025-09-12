import os
from typing import List

# Environment variables with defaults
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./workly.db")
SECRET_KEY = os.getenv("SECRET_KEY", "workly-dev-secret-key-2025")
ENV = os.getenv("ENV", "development")

# CORS settings
ALLOWED_ORIGINS_STR = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS_STR.split(",") if origin.strip()]

# Work time settings
WORK_START_TIME = os.getenv("WORK_START_TIME", "09:30")
WORK_END_TIME = os.getenv("WORK_END_TIME", "18:00")
CHECK_IN_START_TIME = os.getenv("CHECK_IN_START_TIME", "07:00")
CHECK_IN_END_TIME = os.getenv("CHECK_IN_END_TIME", "11:00")
CHECK_OUT_START_TIME = os.getenv("CHECK_OUT_START_TIME", "16:00")
CHECK_OUT_END_TIME = os.getenv("CHECK_OUT_END_TIME", "20:00")

# File upload settings
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "5242880"))  # 5MB
UPLOAD_PATH = os.getenv("UPLOAD_PATH", "./uploads")
ALLOWED_IMAGE_FORMATS_STR = os.getenv("ALLOWED_IMAGE_FORMATS", "jpg,jpeg,png,gif,webp")
ALLOWED_IMAGE_FORMATS = [fmt.strip().lower() for fmt in ALLOWED_IMAGE_FORMATS_STR.split(",")]

# Face ID settings
MAX_FACES_PER_EMPLOYEE = int(os.getenv("MAX_FACES_PER_EMPLOYEE", "3"))
FACE_RECOGNITION_TOLERANCE = float(os.getenv("FACE_RECOGNITION_TOLERANCE", "0.6"))
FACE_RECOGNITION_MODEL = os.getenv("FACE_RECOGNITION_MODEL", "hog")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Bot settings (optional)
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = []
if ADMIN_IDS_STR:
    try:
        ADMIN_IDS = [int(id.strip()) for id in ADMIN_IDS_STR.split(",") if id.strip().isdigit()]
    except ValueError:
        ADMIN_IDS = []

# Utility functions
def is_development() -> bool:
    """Check if running in development mode"""
    return ENV.lower() in ("development", "dev", "debug")

def is_production() -> bool:
    """Check if running in production mode"""
    return ENV.lower() in ("production", "prod")

def get_cors_origins() -> List[str]:
    """Get CORS allowed origins"""
    if is_development():
        # В режиме разработки добавляем localhost варианты
        dev_origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8080",
            "http://127.0.0.1:8080"
        ]
        origins = ALLOWED_ORIGINS.copy()
        for origin in dev_origins:
            if origin not in origins:
                origins.append(origin)
        return origins
    return ALLOWED_ORIGINS

# PostgreSQL async uchun:
# DATABASE_URL = "postgresql+asyncpg://user:password@localhost/workly"
