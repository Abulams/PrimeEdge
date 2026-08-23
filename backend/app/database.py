import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "market_os.db")).replace("\\", "/")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{_DB_PATH}")


# SQLite needs connect_args={"check_same_thread": False, "timeout": 60} to handle concurrent access
if DATABASE_URL.startswith("sqlite"):
    from sqlalchemy import event
    engine = create_engine(
        DATABASE_URL, connect_args={"check_same_thread": False, "timeout": 60}
    )
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=60000")
        cursor.close()
else:
    engine = create_engine(DATABASE_URL)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
