from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log
import logging
import os
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# --------------------------------------------------------
# Retry decorator for transient DB connection errors
# Catches psycopg2.OperationalError / sqlalchemy OperationalError
# Uses exponential backoff: 2s, 4s, up to 10s, max 3 attempts
# --------------------------------------------------------
db_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(OperationalError),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Configure connection pool with better error handling
# IMPORTANT: With large batch operations (7 concurrent batches) and multiple API calls,
# we need a generous pool size to prevent "no available connections" errors
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,              # Test connections before using them (health check)
    pool_recycle=300,                # Recycle connections every 5 minutes to prevent firewall/proxy timeouts
    pool_size=20,                    # Increased from 5 to handle concurrent batch operations
    max_overflow=20,                 # Increased from 10 to 20 for peak load
    echo=False,                      # Disable SQL query logging
    # Connection timeout: 30 seconds to prevent hanging on broken connections
    connect_args={
        "connect_timeout": 30,
        # PostgreSQL idle transaction timeout
        "options": "-c statement_timeout=600000"  # 10 minute statement timeout
    }
)

# Handle "server closed connection unexpectedly" by disposing idle connections
@event.listens_for(engine, "engine_disposed")
def receive_engine_disposed(engine):
    print("[DB] Engine disposed, connections will be recycled")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """
    FastAPI dependency that yields a DB session.
    On OperationalError (e.g. server closed the connection unexpectedly),
    it disposes the connection pool and resets the session, then re-raises
    so that tenacity or the caller can retry.
    """
    db = SessionLocal()
    try:
        yield db
    except OperationalError as e:
        print(f"[DB] OperationalError detected, disposing pool: {e}")
        db.rollback()
        # Dispose all connections in the pool to force fresh connections
        engine.dispose()
        raise
    except Exception as e:
        print(f"[DB] Session error: {e}")
        db.rollback()
        raise
    finally:
        try:
            db.close()
        except Exception as e:
            print(f"[DB] Error closing session (non-fatal): {e}")
