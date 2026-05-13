"""
Run this script once to create an admin superuser:
    .\venv\Scripts\python create_superuser.py
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

username = "admin"
email = "admin@airsoftstore.com"
password = "Admin1234!"  # Change this immediately after first login

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f"Superuser '{username}' created. Password: {password}")
    print("IMPORTANT: Change your password after first login!")
else:
    print(f"Superuser '{username}' already exists.")
