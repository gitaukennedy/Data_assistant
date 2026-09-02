#!/usr/bin/env python3
"""Seed PostgreSQL database with sample business data."""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL")
engine = create_engine(db_url)

# SQL statements to create and populate sample business tables
setup_sql = """
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    customer_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    region VARCHAR(50) NOT NULL,
    signup_date DATE DEFAULT CURRENT_DATE
);

CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(customer_id),
    product VARCHAR(100) NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    order_date DATE DEFAULT CURRENT_DATE
);

INSERT INTO customers (name, email, region) VALUES
('Alice Johnson', 'alice@example.com', 'North America'),
('Bob Smith', 'bob@example.com', 'Europe'),
('Charlie Brown', 'charlie@example.com', 'Asia-Pacific'),
('Diana Prince', 'diana@example.com', 'North America'),
('Eve Wilson', 'eve@example.com', 'Europe');

INSERT INTO orders (customer_id, product, amount, order_date) VALUES
(1, 'Enterprise Subscription', 2500.00, '2026-01-15'),
(1, 'Support Package', 500.00, '2026-02-01'),
(2, 'Pro Plan', 1200.00, '2026-02-10'),
(3, 'Basic Plan', 300.00, '2026-03-05'),
(4, 'Enterprise Subscription', 2500.00, '2026-03-12'),
(5, 'Pro Plan', 1200.00, '2026-03-20'),
(2, 'Support Package', 500.00, '2026-04-01'),
(1, 'Pro Plan', 1200.00, '2026-04-10');
"""

try:
    with engine.connect() as connection:
        connection.execute(text(setup_sql))
        connection.commit()
    print("✅ PostgreSQL database successfully seeded with business data!")
    print("\nDatabase schema:")
    print("- customers: customer_id, name, email, region, signup_date")
    print("- orders: order_id, customer_id, product, amount, order_date")
except Exception as e:
    print(f"❌ Error seeding database: {e}")
    exit(1)