"""Strict allow-list validation for model-generated read-only SQL."""
import re

class SQLValidator:
    """Reject anything other than a single, ordinary SELECT statement."""

    FORBIDDEN_TOKENS = {
        'ALTER', 'ANALYZE', 'CALL', 'COPY', 'CREATE', 'DELETE', 'DO', 'DROP',
        'EXEC', 'EXECUTE', 'GRANT', 'INSERT', 'MERGE', 'REINDEX', 'REPLACE',
        'REVOKE', 'TRUNCATE', 'UPDATE', 'VACUUM',
    }
    FORBIDDEN_PATTERNS = (
        r'--', r'/\*', r'\*/', r';', r'\bINTO\b', r'\bFOR\s+(UPDATE|SHARE)\b',
        r'\bPG_[A-Z0-9_]*', r'\bINFORMATION_SCHEMA\b', r'\bPG_CATALOG\b',
    )

    @classmethod
    def is_safe_query(cls, query: str) -> tuple[bool, str]:
        """Require one comment-free SELECT query with no modifying operations."""
        if not isinstance(query, str) or not query.strip():
            return False, 'The generated SQL was empty.'
        cleaned = query.strip()
        if not re.match(r'^SELECT\b', cleaned, flags=re.IGNORECASE):
            return False, 'Only a single SELECT query is allowed.'

        upper = cleaned.upper()
        if any(re.search(pattern, upper) for pattern in cls.FORBIDDEN_PATTERNS):
            return False, 'The generated SQL contains a disallowed operation.'
        if any(re.search(rf'\b{token}\b', upper) for token in cls.FORBIDDEN_TOKENS):
            return False, 'The generated SQL contains a disallowed operation.'
        return True, ''

    @staticmethod
    def with_row_limit(query: str, limit: int) -> str:
        """Add a server-side result cap when the model omitted one."""
        if re.search(r'\bLIMIT\s+\d+\b', query, flags=re.IGNORECASE):
            return query.strip()
        return f'{query.strip()} LIMIT {limit}'
