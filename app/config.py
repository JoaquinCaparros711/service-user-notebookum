import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    PERSISTENCE_URL = os.environ.get("PERSISTENCE_URL", "http://persistence:5003")
    REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
