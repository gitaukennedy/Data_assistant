"""SQL Query Validator to ensure safe database operations."""
import re
from typing import Tuple

class SQLValidator:
    """Validates SQL queries to prevent destructive operations."""
    
    # Dangerous SQL keywords that are blocked
    DANGEROUS_KEYWORDS = [
        'DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'INSERT', 
        'UPDATE', 'CREATE', 'REPLACE', 'EXEC', 'EXECUTE'
    ]
    
    @staticmethod
    def is_safe_query(query: str) -> Tuple[bool, str]:
        """Validate if a SQL query is safe to execute.
        
        Args:
            query: SQL query string to validate
            
        Returns:
            Tuple of (is_safe: bool, error_message: str)
        """
        # Convert to uppercase for keyword checking
        query_upper = query.strip().upper()
        
        # Check if query starts with SELECT (read-only)
        if not query_upper.startswith('SELECT'):
            return False, "Only SELECT queries are allowed. Destructive operations are blocked."
        
        # Check for dangerous keywords
        for keyword in SQLValidator.DANGEROUS_KEYWORDS:
            if keyword in query_upper:
                return False, f"Keyword '{keyword}' is not allowed for security reasons."
        
        # Check for SQL injection patterns
        injection_patterns = [
            r"(--|#|/\*).*",  # Comments
            r"[;'].*[;']",     # Multiple statements
            r"(?i)union.*select",  # UNION-based injection
        ]
        
        for pattern in injection_patterns:
            if re.search(pattern, query):
                return False, "Potential SQL injection detected."
        
        return True, ""
    
    @staticmethod
    def sanitize_query(query: str) -> str:
        """Sanitize query by removing comments and extra whitespace.
        
        Args:
            query: Raw SQL query
            
        Returns:
            Sanitized query
        """
        # Remove SQL comments
        query = re.sub(r'--.*$', '', query, flags=re.MULTILINE)
        query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)
        
        # Remove extra whitespace
        query = ' '.join(query.split())
        
        return query.strip()