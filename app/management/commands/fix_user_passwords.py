from django.core.management.base import BaseCommand
from app.models import User
from django.contrib.auth.hashers import make_password

def is_hashed(password):
    # Django hashed passwords start with the algorithm prefix, e.g. 'pbkdf2_sha256$'
    return password.startswith('pbkdf2_') or password.startswith('argon2$') or password.startswith('bcrypt$')

class Command(BaseCommand):
    help = 'Check all users for email and password, and hash plain text passwords if needed.'

    def handle(self, *args, **options):
        users = User.objects.all()
        updated = 0
        for user in users:
            if not user.email:
                self.stdout.write(self.style.WARNING(f'User {user.username} is missing an email.'))
            if not user.password:
                self.stdout.write(self.style.WARNING(f'User {user.username} is missing a password.'))
            elif not is_hashed(user.password):
                # Hash the plain text password
                user.password = make_password(user.password)
                user.save()
                updated += 1
                self.stdout.write(self.style.SUCCESS(f'Password for user {user.username} was hashed.'))
        self.stdout.write(self.style.SUCCESS(f'Checked {users.count()} users. {updated} password(s) updated.'))
