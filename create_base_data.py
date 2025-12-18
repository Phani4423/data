#!/usr/bin/env python
"""
Script to create base data for testing: Organizations, Users, and Policies.
"""

import os
import django
from django.contrib.auth import get_user_model

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data.settings')
django.setup()

from app.models import Organization, Policy

def create_base_data():
    """Create base data for testing"""
    print("🏗️ Creating Base Data for Testing...")
    print("=" * 50)

    # Create Organizations
    print("🏢 Creating Organizations...")
    org1 = Organization.objects.create(name="TechCorp", location="New York")
    org2 = Organization.objects.create(name="DataInc", location="San Francisco")
    print(f"   ✓ Created {org1.name}")
    print(f"   ✓ Created {org2.name}")

    # Create Users
    print("\n👥 Creating Users...")
    User = get_user_model()

    # Manager user
    manager = User.objects.create_user(
        username="manager",
        email="manager@techcorp.com",
        password="password123",
        role="manager"
    )
    manager.organizations.add(org1)
    print(f"   ✓ Created manager user: {manager.username}")

    # Analyst users
    analyst1 = User.objects.create_user(
        username="analyst1",
        email="analyst1@techcorp.com",
        password="password123",
        role="analyst",
        organization=org1
    )
    print(f"   ✓ Created analyst user: {analyst1.username}")

    analyst2 = User.objects.create_user(
        username="analyst2",
        email="analyst2@datainc.com",
        password="password123",
        role="analyst",
        organization=org2
    )
    print(f"   ✓ Created analyst user: {analyst2.username}")

    # Create Policies
    print("\n🔐 Creating Policies...")

    # Manager policy - full access
    Policy.objects.create(
        user=manager,
        can_upload=True,
        can_read=True,
        can_delete=True,
        can_read_all_files=True,
        can_add_user=True,
        can_delete_user=True,
        can_set_permissions=True
    )
    print(f"   ✓ Created policy for {manager.username} (full access)")

    # Analyst1 policy - limited access
    Policy.objects.create(
        user=analyst1,
        can_upload=True,
        can_read=True,
        can_delete=False,
        can_read_all_files=False,
        can_add_user=False,
        can_delete_user=False,
        can_set_permissions=False
    )
    print(f"   ✓ Created policy for {analyst1.username} (upload/read only)")

    # Analyst2 policy - read only
    Policy.objects.create(
        user=analyst2,
        can_upload=False,
        can_read=True,
        can_delete=False,
        can_read_all_files=False,
        can_add_user=False,
        can_delete_user=False,
        can_set_permissions=False
    )
    print(f"   ✓ Created policy for {analyst2.username} (read only)")

    print("\n✅ Base Data Created Successfully!")
    print("\n📋 Summary:")
    print(f"   Organizations: {Organization.objects.count()}")
    print(f"   Users: {User.objects.count()}")
    print(f"   Policies: {Policy.objects.count()}")

if __name__ == "__main__":
    create_base_data()
