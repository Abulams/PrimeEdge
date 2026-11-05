import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Candidate paths for the SQLite database
_POSSIBLE_PATHS = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "market_os.db")),
    os.path.abspath("backend/market_os.db"),
    os.path.abspath("market_os.db"),
    os.path.abspath("./backend/market_os.db"),
    os.path.abspath("./market_os.db"),
]

# Find the populated production DB (largest file size, ~14.5 MB, not an empty 4KB stub)
_BEST_DB_PATH = _POSSIBLE_PATHS[0]
_max_size = -1
for _p in _POSSIBLE_PATHS:
    if os.path.exists(_p):
        _sz = os.path.getsize(_p)
        if _sz > _max_size:
            _max_size = _sz
            _BEST_DB_PATH = _p

# If DATABASE_URL is set to an empty 4KB SQLite file, prefer the populated 14MB file
_env_db_url = os.getenv("DATABASE_URL")
if _env_db_url and _env_db_url.startswith("sqlite:///"):
    _clean_path = _env_db_url.replace("sqlite:///", "")
    if os.path.exists(_clean_path) and os.path.getsize(_clean_path) > 1000000:
        DATABASE_URL = _env_db_url
    elif _max_size > 1000000:
        DATABASE_URL = f"sqlite:///{_BEST_DB_PATH.replace(os.sep, '/')}"
    else:
        DATABASE_URL = _env_db_url
else:
    DATABASE_URL = _env_db_url or f"sqlite:///{_BEST_DB_PATH.replace(os.sep, '/')}"

print(f"[DB] Initialized DATABASE_URL={DATABASE_URL} (size={_max_size} bytes)")

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
