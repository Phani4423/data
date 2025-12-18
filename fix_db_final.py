#!/usr/bin/env python
import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data.settings')
django.setup()

cursor = connection.cursor()

print("🔧 Final database schema fix...")

try:
    # Check current columns
    cursor.execute("DESCRIBE app_user")
    columns = [row[0] for row in cursor.fetchall()]
    print(f"Current columns: {columns}")

    # Add created_at if missing
    if 'created_at' not in columns:
        cursor.execute("ALTER TABLE app_user ADD COLUMN created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP")
        print("✓ Added created_at column")

    # Create many-to-many table if it doesn't exist
    cursor.execute("SHOW TABLES LIKE 'app_user_organizations'")
    if not cursor.fetchone():
        cursor.execute("""
            CREATE TABLE app_user_organizations (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                organization_id BIGINT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES app_user(id) ON DELETE CASCADE,
                FOREIGN KEY (organization_id) REFERENCES app_organization(id) ON DELETE CASCADE,
                UNIQUE KEY user_organization (user_id, organization_id)
            )
        """)
        print("✓ Created app_user_organizations table")

    # Remove organization_id if it exists
    if 'organization_id' in columns:
        # First drop the foreign key constraint
        try:
            cursor.execute("ALTER TABLE app_user DROP FOREIGN KEY app_user_organization_id_c85e9ed7_fk_app_organization_id")
            print("✓ Dropped foreign key constraint")
        except:
            print("No foreign key constraint to drop")

        # Then drop the column
        cursor.execute("ALTER TABLE app_user DROP COLUMN organization_id")
        print("✓ Dropped organization_id column")

    print("✅ Database schema fixed successfully")

except Exception as e:
    print(f"❌ Error: {e}")
