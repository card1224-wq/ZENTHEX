import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = os.getenv("ZENTHEX_DATABASE_URL", "sqlite:///./zenthex.db")
# Use a persistent database in production, for example:
# ZENTHEX_DATABASE_URL=postgresql://user:password@postgresserver/db
# If the deploy server starts with a fresh local SQLite file, old GitHub-uploaded accounts will not exist.

connect_args = {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
