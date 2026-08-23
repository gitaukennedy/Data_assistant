from sqlalchemy import create_engine, text

# Connect to default postgres DB
engine = create_engine("postgresql+psycopg2://postgres:0000@localhost:5432/postgres")

with engine.connect() as conn:
    conn.execution_options(isolation_level="AUTOCOMMIT").execute(text("CREATE DATABASE company_db;"))
    print("Database company_db created successfully.")