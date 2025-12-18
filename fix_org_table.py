#!/usr/bin/env python
import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data.settings')
django.setup()

cursor = connection.cursor()

print("🔧 Fixing Organization table...")

try:
    # Check current columns in app_organization
    cursor.execute("DESCRIBE app_organization")
    columns = [row[0] for row in cursor.fetchall()]
    print(f"Current columns: {columns}")

    # Add created_at if missing
    if 'created_at' not in columns:
        cursor.execute("ALTER TABLE app_organization ADD COLUMN created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP")
        print("✓ Added created_at column to app_organization")

    print("✅ Organization table fixed successfully")

except Exception as e:
    print(f"❌ Error: {e}")
