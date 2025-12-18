#!/usr/bin/env python
import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data.settings')
django.setup()

cursor = connection.cursor()
cursor.execute("DESCRIBE app_user;")
columns = cursor.fetchall()
print("app_user table columns:")
for col in columns:
    print(f"  {col[0]} - {col[1]}")
