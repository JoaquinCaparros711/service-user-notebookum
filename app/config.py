import os
from dotenv import load_dotenv
from app.utils.consul_kv import get as kv, get_int as kv_int

load_dotenv()

class Config:
    # Consul KV → env var → hard-coded safe default
    SECRET_KEY = kv("secret_key", os.environ.get("SECRET_KEY", "dev-secret-key"))
    PERSISTENCE_URL = kv("persistence_url", os.environ.get("PERSISTENCE_URL", "http://persistence-java.universidad.localhost:8080"))
    REDIS_URL = kv("redis_url", os.environ.get("REDIS_URL", "redis://redis:6379/0"))
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRATION_SECONDS = kv_int("jwt_expiration_seconds", int(os.environ.get("JWT_EXPIRATION_SECONDS", "3600")))
    JWT_REFRESH_EXPIRATION_DAYS = kv_int("jwt_refresh_expiration_days", int(os.environ.get("JWT_REFRESH_EXPIRATION_DAYS", "7")))

