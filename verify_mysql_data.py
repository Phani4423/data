#!/usr/bin/env python
"""
Script to verify that all Django model data is properly stored in MySQL database
and visible in the database tables.
"""

import os
import sys
import django
from django.db import connection

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data.settings')
django.setup()

from app.models import User, Organization, Policy, UploadedFile, FileUpdateLog

def verify_database_tables():
    """Verify that all required tables exist in MySQL"""
    print("🔍 Checking MySQL Database Tables...")
    print("=" * 50)

    cursor = connection.cursor()
    cursor.execute("SHOW TABLES;")
    tables = [row[0] for row in cursor.fetchall()]

    required_tables = [
        'app_user',
        'app_organization',
        'app_policy',
        'app_uploadedfile',
        'app_fileupdatelog'
    ]

    print("✅ Required Django Model Tables:")
    for table in required_tables:
        if table in tables:
            print(f"   ✓ {table} - EXISTS")
        else:
            print(f"   ✗ {table} - MISSING")

    print("\n📊 Custom Data Tables (from file uploads):")
    custom_tables = [t for t in tables if t not in required_tables and not t.startswith(('auth_', 'django_', 'authtoken_'))]
    for table in custom_tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table};")
        count = cursor.fetchone()[0]
        print(f"   📄 {table} - {count} records")

    return tables

def verify_model_data():
    """Verify data in Django models"""
    print("\n🔍 Checking Django Model Data...")
    print("=" * 50)

    # Users
    users = User.objects.all()
    print(f"👥 Users ({users.count()} total):")
    for user in users[:5]:  # Show first 5
        org = user.organization.name if user.organization else "No Organization"
        print(f"   • {user.username} - {org}")
    if users.count() > 5:
        print(f"   ... and {users.count() - 5} more")

    # Organizations
    orgs = Organization.objects.all()
    print(f"\n🏢 Organizations ({orgs.count()} total):")
    for org in orgs:
        print(f"   • {org.name}")

    # Policies
    policies = Policy.objects.all()
    print(f"\n🔐 Policies ({policies.count()} total):")
    for policy in policies[:5]:
        print(f"   • {policy.user.username} - upload:{policy.can_upload}, read:{policy.can_read}")

    # Uploaded Files
    uploads = UploadedFile.objects.all()
    print(f"\n📁 Uploaded Files ({uploads.count()} total):")
    for upload in uploads:
        print(f"   • {upload.filename} - table: {upload.table_name}")

def verify_mysql_direct_queries():
    """Direct MySQL queries to show data visibility"""
    print("\n🔍 Direct MySQL Queries (What you'll see in MySQL client)...")
    print("=" * 50)

    cursor = connection.cursor()

    # Show users
    print("👥 Users in MySQL (SELECT * FROM app_user LIMIT 3):")
    cursor.execute("SELECT id, username, email, organization_id FROM app_user LIMIT 3;")
    users = cursor.fetchall()
    for user in users:
        print(f"   {user}")

    # Show organizations
    print("\n🏢 Organizations in MySQL (SELECT * FROM app_organization):")
    cursor.execute("SELECT id, name, location FROM app_organization;")
    orgs = cursor.fetchall()
    for org in orgs:
        print(f"   {org}")

    # Show policies
    print("\n🔐 Policies in MySQL (SELECT * FROM app_policy LIMIT 3):")
    cursor.execute("SELECT id, user_id, can_upload, can_read, can_delete FROM app_policy LIMIT 3;")
    policies = cursor.fetchall()
    for policy in policies:
        print(f"   {policy}")

    # Show uploaded files
    print("\n📁 Uploaded Files in MySQL (SELECT * FROM app_uploadedfile):")
    cursor.execute("SELECT id, user_id, filename, table_name, uploaded_at FROM app_uploadedfile;")
    uploads = cursor.fetchall()
    for upload in uploads:
        print(f"   {upload}")

    # Show sample from custom tables
    cursor.execute("SHOW TABLES;")
    tables = [row[0] for row in cursor.fetchall()]
    custom_tables = [t for t in tables if t not in ['app_user', 'app_organization', 'app_policy', 'app_uploadedfile', 'app_fileupdatelog'] and not t.startswith(('auth_', 'django_', 'authtoken_'))]

    if custom_tables:
        print(f"\n📊 Sample Data from Custom Tables:")
        for table in custom_tables[:2]:  # Show first 2 custom tables
            cursor.execute(f"SELECT COUNT(*) FROM {table};")
            count = cursor.fetchone()[0]
            print(f"   📄 {table}: {count} records")
            if count > 0:
                cursor.execute(f"SELECT * FROM {table} LIMIT 1;")
                sample = cursor.fetchone()
                print(f"      Sample row: {sample[:5]}...")  # Show first 5 columns

def main():
    print("🚀 MySQL Data Verification Script")
    print("This script verifies that all data insertions are properly stored in MySQL")
    print()

    try:
        verify_database_tables()
        verify_model_data()
        verify_mysql_direct_queries()

        print("\n✅ VERIFICATION COMPLETE!")
        print("\n📋 Summary for MySQL Client:")
        print("   • Database: new_etl_db")
        print("   • Host: localhost:3306")
        print("   • User: root")
        print("   • Tables to check:")
        print("     - app_user (user accounts)")
        print("     - app_organization (organizations)")
        print("     - app_policy (ABAC permissions)")
        print("     - app_uploadedfile (file upload metadata)")
        print("     - app_fileupdatelog (file operation logs)")
        print("     - Custom tables (random_users, orders5, etc. - actual uploaded data)")

    except Exception as e:
        print(f"❌ Error during verification: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
