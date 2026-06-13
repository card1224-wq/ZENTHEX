import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = os.getenv("ZENTHEX_DATABASE_URL", "sqlite:///./zenthex.db")
# Use a persistent database in production, for example:
# ZENTHEX_DATABASE_URL=postgresql://user:password@postgresserver/db
# If the deploy server starts with a fresh local SQLite file, old GitHub-uploaded accounts will not exist.

def normalize_database_url(url: str) -> str:
    # Some hosts expose postgres://, while SQLAlchemy expects postgresql://.
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url

SQLALCHEMY_DATABASE_URL = normalize_database_url(SQLALCHEMY_DATABASE_URL)

def is_sqlite_database() -> bool:
    return SQLALCHEMY_DATABASE_URL.startswith("sqlite")

connect_args = {"check_same_thread": False} if is_sqlite_database() else {}
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
