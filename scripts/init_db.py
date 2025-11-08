"""
Initialize database schema.
Run this to create all tables in PostgreSQL.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database import init_db


def main():
    """Initialize database schema."""
    print("Initializing database schema...")

    # For test database
    os.environ['DATABASE_URL'] = 'postgresql://hazeuser:testpassword@localhost:5432/haze_prediction_test'
    test_engine = init_db()
    print(f"Test database initialized: {test_engine.url}")

    # For production database
    os.environ['DATABASE_URL'] = 'postgresql://hazeuser:testpassword@localhost:5432/haze_prediction'
    prod_engine = init_db()
    print(f"Production database initialized: {prod_engine.url}")

    print("Database initialization complete!")


if __name__ == '__main__':
    main()
