import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    PERSISTENCE_URL = os.environ.get("PERSISTENCE_URL", "http://persistence:5000")
    REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRATION_SECONDS = int(os.environ.get("JWT_EXPIRATION_SECONDS", "3600"))  # 1 hour
    JWT_REFRESH_EXPIRATION_DAYS = int(os.environ.get("JWT_REFRESH_EXPIRATION_DAYS", "7"))  # 7 days

