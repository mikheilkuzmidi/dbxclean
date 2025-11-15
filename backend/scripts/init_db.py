#!/usr/bin/env python3
"""
Database initialization script
Run this before starting the application for the first time
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import init_db, engine
from app.models import Base
from sqlalchemy import inspect


def check_tables():
    """Check if tables exist"""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    return tables


def main():
    print("🗄️  Initializing Dropbox Sorter database...")

    # Check existing tables
    existing_tables = check_tables()

    if existing_tables:
        print(f"📋 Found existing tables: {', '.join(existing_tables)}")
        response = input("Do you want to recreate all tables? This will DELETE all data! (yes/no): ")

        if response.lower() == 'yes':
            print("⚠️  Dropping all tables...")
            Base.metadata.drop_all(bind=engine)
            print("✅ Tables dropped")

    # Create all tables
    print("📝 Creating database tables...")
    init_db()

    # Verify tables were created
    tables = check_tables()
    print(f"✅ Database initialized successfully!")
    print(f"📋 Created tables: {', '.join(tables)}")

    expected_tables = ['file_metadata', 'duplicate_groups', 'similar_groups', 'analysis_jobs']
    missing = set(expected_tables) - set(tables)

    if missing:
        print(f"⚠️  Warning: Missing expected tables: {', '.join(missing)}")
        return 1

    print("✅ All tables created successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
