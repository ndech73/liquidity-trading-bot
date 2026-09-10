from loguru import logger
from app.db.base import Base
from app.db.session import engine
import app.db.models  # noqa: F401


def init_db() -> bool:
    """Creates database tables if they do not already exist."""
    try:
        logger.info("Initializing database tables...")
        Base.metadata.create_all(bind=engine)
        logger.success("Database tables initialized successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}")
        return False
