"""
Database configuration.
Uses SQLAlchemy with SQLite by default (easily swappable to PostgreSQL via .env).
Assumption: SQLite is sufficient for assessment; production would use PostgreSQL.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./finance_dashboard.db")

# connect_args only needed for SQLite (multi-thread safety)
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
