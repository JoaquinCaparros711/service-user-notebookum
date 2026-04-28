import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    PERSISTENCE_URL = os.environ.get("PERSISTENCE_URL", "http://persistence:5003")
