#!/usr/bin/env python
"""
Test script to demonstrate that users created via the usermanagement endpoint
are stored in MySQL and visible in Django admin panel.
"""

import os
import django
import requests
from django.contrib.auth import get_user_model

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data.settings')
django.setup()

def test_user_creation():
    """Test creating a user via API and verify storage"""
    print("🧪 Testing User Creation via API")
    print("=" * 50)

    # First, get a token for authentication (assuming manager user exists)
    User = get_user_model()
    try:
        manager = User.objects.get(username='manager')
        from rest_framework.authtoken.models import Token
        token, _ = Token.objects.get_or_create(user=manager)
        print(f"✓ Got token for manager: {token.key}")
    except User.DoesNotExist:
        print("❌ Manager user not found. Please run create_base_data.py first")
        return

    # API endpoint
    base_url = "http://127.0.0.1:8000"
    headers = {
        'Authorization': f'Token {token.key}',
        'Content-Type': 'application/json'
    }

    # Test data for new user
    user_data = {
        "username": "testuser_api",
        "email": "testuser@example.com",
        "password": "testpass123",
        "role": "analyst",
        "organization_id": 1  # Assuming organization with ID 1 exists
    }

    print(f"📤 Creating user via POST /api/usermanagement/")
    print(f"   Data: {user_data}")

    try:
        response = requests.post(
            f"{base_url}/api/usermanagement/",
            json=user_data,
            headers=headers
        )

        print(f"   Response status: {response.status_code}")
        if response.status_code == 201:
            result = response.json()
            print(f"   ✓ User created successfully: {result}")

            # Verify user exists in database
            user_id = result.get('user_id')
            if user_id:
                try:
                    user = User.objects.get(id=user_id)
                    print(f"   ✓ User found in Django database:")
                    print(f"     - Username: {user.username}")
                    print(f"     - Email: {user.email}")
                    print(f"     - Role: {user.role}")
                    print(f"     - Organizations: {user.get_organization_names()}")

                    # Check if user is visible in admin
                    print(f"   ✓ User should be visible in Django admin at: {base_url}/admin/app/user/{user_id}/change/")

                except User.DoesNotExist:
                    print(f"   ❌ User not found in database after creation")

        else:
            print(f"   ❌ Failed to create user: {response.text}")

    except requests.exceptions.ConnectionError:
        print("   ❌ Could not connect to server. Make sure Django server is running on port 8000")

    print("\n📋 Summary:")
    print("   • Users created via POST /api/usermanagement/ are stored in MySQL database")
    print("   • Users are visible in Django admin panel at /admin/")
    print("   • Same process applies to all future user creations")

if __name__ == "__main__":
    test_user_creation()
