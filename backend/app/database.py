# backend/app/database.py

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set.\n"
        "Set it in your Render dashboard (or .env for local dev).\n"
        "Format: postgresql://USER:PASSWORD@HOST:5432/postgres?sslmode=require"
    )

# ---------------------------------------------------------------
# Supabase requires SSL. Auto-append sslmode=require if missing.
# ---------------------------------------------------------------
if "supabase.co" in DATABASE_URL and "sslmode" not in DATABASE_URL:
    sep = "&" if "?" in DATABASE_URL else "?"
    DATABASE_URL = DATABASE_URL + sep + "sslmode=require"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,   # reconnect after idle timeouts (important for Supabase)
    pool_recycle=300,     # recycle connections every 5 min
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    FastAPI dependency — provides a SQLAlchemy session
    and ensures it is closed after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
