#!/usr/bin/env python3
"""Create PostgreSQL database."""

from sqlalchemy import create_engine, text

# Connect to default postgres DB
engine = create_engine("postgresql+psycopg2://postgres:0000@localhost:5432/postgres")

try:
    with engine.connect() as conn:
        conn.execution_options(isolation_level="AUTOCOMMIT").execute(
            text("CREATE DATABASE company_db;")
        )
    print("✅ Database company_db created successfully.")
except Exception as e:
    if "already exists" in str(e):
        print("⚠️  Database company_db already exists.")
    else:
        print(f"❌ Error creating database: {e}")
        exit(1)