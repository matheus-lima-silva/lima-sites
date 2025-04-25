import os

from dotenv import load_dotenv

load_dotenv()

# Use SQLite como padrão para desenvolvimento
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./dev.db")
SECRET_KEY = os.getenv("SECRET_KEY", "changeme")
DEBUG = os.getenv("DEBUG", "False") == "True"


# Classe de configurações para uso com FastAPI, etc.
class Settings:
    DATABASE_URL: str = DATABASE_URL
    SECRET_KEY: str = SECRET_KEY
    DEBUG: bool = DEBUG
