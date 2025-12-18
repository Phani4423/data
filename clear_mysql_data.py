#!/usr/bin/env python
"""
Script to clear all data from MySQL database tables.
"""

import os
import sys
import django
from django.db import connection

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data.settings')
django.setup()

def clear_mysql_data():
    """Clear all data from MySQL tables"""
    print("🗑️ Clearing MySQL Database Data...")
    print("=" * 50)

    cursor = connection.cursor()

    # List of tables to clear (excluding Django system tables)
    # Delete in order to respect foreign keys: children first, then parents
    tables_to_clear = [
        'authtoken_token',  # Child of app_user
        'app_uploadedfile',  # Child of app_user
        'app_policy',  # Child of app_user
        'app_user_organizations',  # Many-to-many table
        'app_fileupdatelog',  # Child of app_user and app_organization
        'app_user',  # Parent
        'app_organization',  # Parent
        # Also clear custom ETL tables if they exist
    ]

    # Get all tables
    cursor.execute("SHOW TABLES;")
    all_tables = [row[0] for row in cursor.fetchall()]

    # Clear Django model tables
    for table in tables_to_clear:
        if table in all_tables:
            cursor.execute(f"DELETE FROM {table};")
            print(f"   ✓ Cleared {table}")

    # Clear custom tables (ETL data)
    custom_tables = [t for t in all_tables if t not in tables_to_clear and not t.startswith(('auth_', 'django_', 'authtoken_', 'celery_'))]
    for table in custom_tables:
        cursor.execute(f"DROP TABLE {table};")
        print(f"   ✓ Dropped custom table {table}")

    # Reset auto-increment counters
    for table in tables_to_clear:
        if table in all_tables:
            try:
                cursor.execute(f"ALTER TABLE {table} AUTO_INCREMENT = 1;")
            except:
                pass  # Some tables may not have auto-increment

    print("\n✅ MySQL Data Cleared Successfully!")

if __name__ == "__main__":
    clear_mysql_data()
