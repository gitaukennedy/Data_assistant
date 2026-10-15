"""Database connection, schema inspection, and safe read-only execution."""
import os
from urllib.parse import urlparse
from sqlalchemy import create_engine, inspect, text
from dotenv import load_dotenv
import logging

from backend.utils.sql_validator import SQLValidator

logger = logging.getLogger(__name__)
load_dotenv()


def normalize_database_url(raw_url: str) -> str:
    """Convert deployment platform URLs into a SQLAlchemy-compatible PostgreSQL URL."""
    if not raw_url:
        return raw_url

    url = raw_url.strip()
    if url.startswith('postgres://'):
        url = 'postgresql://' + url[len('postgres://'):]

    parsed = urlparse(url)
    if parsed.scheme == 'postgresql' and parsed.netloc and not parsed.path:
        return url + '/postgres'

    return url


class DatabaseManager:
    """Manages database access without coupling the application to LangChain."""
    
    def __init__(self, database_url: str = None):
        """Initialize a pooled SQLAlchemy database connection."""
        raw_db_url = database_url or os.getenv("DATABASE_URL")
        if not raw_db_url:
            raise ValueError("DATABASE_URL environment variable not set")

        self.db_url = normalize_database_url(raw_db_url)
        try:
            engine_options = {"pool_pre_ping": True}
            # SQLite's in-memory pool does not accept QueuePool sizing options;
            # keeping this branch also makes the offline tests representative.
            if not self.db_url.startswith("sqlite:"):
                engine_options.update(
                    pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
                    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "5")),
                )
            self.engine = create_engine(self.db_url, **engine_options)
            logger.info("Database engine configured")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def get_table_schemas(self) -> dict:
        """Retrieve all table schemas.
        
        Returns:
            Dictionary with table names and their schemas
        """
        inspector = inspect(self.engine)
        schemas = {}
        
        for table_name in inspector.get_table_names():
            columns = inspector.get_columns(table_name)
            schemas[table_name] = {
                'columns': [{col['name']: str(col['type'])} for col in columns],
                'primary_key': inspector.get_pk_constraint(table_name).get('constrained_columns', [])
            }
        
        return schemas
    
    def execute_safe_select(self, query: str) -> list[dict]:
        """Validate and execute one bounded SELECT, returning row mappings."""
        is_safe, reason = SQLValidator.is_safe_query(query)
        if not is_safe:
            raise ValueError(reason)

        statement = SQLValidator.with_row_limit(query, limit=100)
        with self.engine.begin() as connection:
            # Production credentials should additionally be a SELECT-only role.
            if connection.dialect.name == 'postgresql':
                connection.execute(text("SET TRANSACTION READ ONLY"))
                timeout_ms = int(os.getenv("DB_STATEMENT_TIMEOUT_MS", "5000"))
                connection.execute(text(f"SET LOCAL statement_timeout = {timeout_ms}"))
            rows = connection.execute(text(statement)).mappings().all()
        return [dict(row) for row in rows]
    
    def health_check(self) -> bool:
        """Check database connectivity.
        
        Returns:
            True if database is accessible
        """
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
