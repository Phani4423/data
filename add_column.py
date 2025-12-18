#!/usr/bin/env python
import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data.settings')
django.setup()

cursor = connection.cursor()

# Add created_at column to app_user table
try:
    cursor.execute("ALTER TABLE app_user ADD COLUMN created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP")
    print("✓ Added created_at column to app_user table")
except Exception as e:
    print(f"Error adding column: {e}")

# Check if organizations many-to-many table exists
try:
    cursor.execute("SHOW TABLES LIKE 'app_user_organizations'")
    if not cursor.fetchone():
        # Create the many-to-many table
        cursor.execute("""
            CREATE TABLE app_user_organizations (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                organization_id BIGINT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES app_user(id),
                FOREIGN KEY (organization_id) REFERENCES app_organization(id),
                UNIQUE KEY user_organization (user_id, organization_id)
            )
        """)
        print("✓ Created app_user_organizations table")
    else:
        print("✓ app_user_organizations table already exists")
except Exception as e:
    print(f"Error with organizations table: {e}")

# Remove organization_id column if it exists
try:
    cursor.execute("DESCRIBE app_user")
    columns = [row[0] for row in cursor.fetchall()]
    if 'organization_id' in columns:
        cursor.execute("ALTER TABLE app_user DROP COLUMN organization_id")
        print("✓ Removed organization_id column from app_user table")
except Exception as e:
    print(f"Error removing organization_id: {e}")

print("Database schema fix completed")
