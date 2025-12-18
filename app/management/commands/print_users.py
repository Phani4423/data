from django.core.management.base import BaseCommand
from app.models import User

class Command(BaseCommand):
    help = 'Print all users with their email and password (for debugging only!)'

    def handle(self, *args, **options):
        users = User.objects.all()
        for user in users:
            self.stdout.write(f"username: {user.username}, email: {user.email}, password: {user.password}")
        self.stdout.write(self.style.SUCCESS(f"Total users: {users.count()}"))
