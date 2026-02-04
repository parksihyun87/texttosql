import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


_raw_url = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/mydb",
)
# psycopg 3 드라이버 명시 (SQLAlchemy용)
DATABASE_URL = _raw_url.replace("postgresql://", "postgresql+psycopg://")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()