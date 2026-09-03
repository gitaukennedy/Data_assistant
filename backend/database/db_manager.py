"""Database connection and schema management."""
import os
from sqlalchemy import create_engine, inspect
from langchain_community.utilities import SQLDatabase
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database connections and schema operations."""
    
    def __init__(self):
        """Initialize database connection."""
        self.db_url = os.getenv("DATABASE_URL")
        if not self.db_url:
            raise ValueError("DATABASE_URL environment variable not set")
        
        try:
            self.db = SQLDatabase.from_uri(self.db_url)
            self.engine = create_engine(self.db_url)
            logger.info("Database connection established")
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
                'primary_key': inspector.get_pk_constraint(table_name)['constrained_columns']
            }
        
        return schemas
    
    def execute_query(self, query: str) -> tuple:
        """Execute a SELECT query safely.
        
        Args:
            query: SQL query to execute
            
        Returns:
            Tuple of (results, column_names)
        """
        try:
            result = self.db.run(query)
            logger.info(f"Query executed successfully")
            return result, []
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    def health_check(self) -> bool:
        """Check database connectivity.
        
        Returns:
            True if database is accessible
        """
        try:
            with self.engine.connect() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False