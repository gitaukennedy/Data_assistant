"""
SQL Executor Module - Handles all SQL operations (SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER)
"""
import os
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv
import pandas as pd
from typing import Dict, List, Any, Tuple

load_dotenv()

class SQLExecutor:
    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL")
        if not self.db_url:
            raise ValueError("DATABASE_URL environment variable not set")
        self.engine = create_engine(self.db_url)
    
    def execute_query(self, sql_query: str) -> Tuple[bool, Any, str]:
        """
        Execute any SQL query (SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, etc.)
        
        Args:
            sql_query: SQL query string
            
        Returns:
            Tuple of (success, data/result, message)
        """
        try:
            sql_query = sql_query.strip()
            
            with self.engine.connect() as connection:
                # Determine query type
                query_type = self._get_query_type(sql_query)
                
                if query_type == "SELECT":
                    result = connection.execute(text(sql_query))
                    df = pd.DataFrame(result.fetchall(), columns=result.keys())
                    return True, df, f"Query executed successfully. Returned {len(df)} rows."
                
                elif query_type in ["INSERT", "UPDATE", "DELETE"]:
                    result = connection.execute(text(sql_query))
                    connection.commit()
                    rows_affected = result.rowcount
                    return True, rows_affected, f"{query_type} operation successful. Rows affected: {rows_affected}"
                
                elif query_type in ["CREATE", "ALTER", "DROP"]:
                    connection.execute(text(sql_query))
                    connection.commit()
                    return True, None, f"{query_type} operation executed successfully."
                
                else:
                    result = connection.execute(text(sql_query))
                    connection.commit()
                    return True, None, f"Query executed successfully."
                    
        except SQLAlchemyError as e:
            error_msg = f"Database Error: {str(e)}"
            return False, None, error_msg
        except Exception as e:
            error_msg = f"Error executing query: {str(e)}"
            return False, None, error_msg
    
    def get_table_schema(self, table_name: str) -> Dict[str, str]:
        """Get schema information for a table"""
        try:
            inspector = inspect(self.engine)
            columns = inspector.get_columns(table_name)
            schema = {col['name']: str(col['type']) for col in columns}
            return schema
        except Exception as e:
            return {"error": str(e)}
    
    def get_all_tables(self) -> List[str]:
        """Get all table names in database"""
        try:
            inspector = inspect(self.engine)
            return inspector.get_table_names()
        except Exception as e:
            return []
    
    @staticmethod
    def _get_query_type(sql_query: str) -> str:
        """Determine the type of SQL query"""
        query_upper = sql_query.upper().strip()
        
        if query_upper.startswith("SELECT"):
            return "SELECT"
        elif query_upper.startswith("INSERT"):
            return "INSERT"
        elif query_upper.startswith("UPDATE"):
            return "UPDATE"
        elif query_upper.startswith("DELETE"):
            return "DELETE"
        elif query_upper.startswith("CREATE"):
            return "CREATE"
        elif query_upper.startswith("ALTER"):
            return "ALTER"
        elif query_upper.startswith("DROP"):
            return "DROP"
        else:
            return "OTHER"
