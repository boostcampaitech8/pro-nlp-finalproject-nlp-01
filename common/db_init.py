import logging
from sqlalchemy import text
from common.database import engine, Base
from common import models

logger = logging.getLogger(__name__)

def init_db():
    """
    Synchronizes the database schema and ensures Enum types are healthy.
    This handles cases where migrations might have missed some values or
    where the DB was initialized with an older schema.
    """
    logger.info("Starting database initialization...")
    try:
        # 1. Create tables if they don't exist
        logger.info("Syncing tables via SQLAlchemy metadata...")
        Base.metadata.create_all(bind=engine)
        logger.info("Table sync complete.")

        # 2. Heal Enum: 'processingstatus'
        # Note: PostgreSQL's ALTER TYPE ... ADD VALUE cannot be executed in a transaction block.
        # We use isolation_level="AUTOCOMMIT" to handle this.
        with engine.connect() as conn:
            # Check if the type exists first
            exists = conn.execute(text("SELECT 1 FROM pg_type WHERE typname = 'processingstatus'")).fetchone()
            
            if exists:
                logger.info("Healing 'processingstatus' enum values...")
                conn = conn.execution_options(isolation_level="AUTOCOMMIT")
                
                # These are the values defined in common/models.py
                expected_values = ["PENDING", "PROCESSING", "REVIEW_REQUIRED", "COMPLETED", "FAILED"]
                
                for val in expected_values:
                    # Using IF NOT EXISTS to avoid errors if value already present
                    # This requires PostgreSQL 9.4+
                    try:
                        conn.execute(text(f"ALTER TYPE processingstatus ADD VALUE IF NOT EXISTS '{val}'"))
                        logger.debug(f"Ensured '{val}' exists in processingstatus.")
                    except Exception as e:
                        # Fallback for older PG or if IF NOT EXISTS has issues in some contexts
                        logger.warning(f"Could not add value '{val}' (it may already exist): {e}")
            else:
                logger.info("'processingstatus' type not found. It will be created when tables using it are created.")

        logger.info("Database initialization finished successfully.")
    except Exception as e:
        logger.error(f"Database initialization encountered an error: {e}")
        # We log and continue, as the app might still be able to function partially
