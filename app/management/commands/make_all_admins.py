from django.core.management.base import BaseCommand
from app.models import User

class Command(BaseCommand):
    help = 'Make all users admins (is_staff and is_superuser True), but keep their role unchanged.'

    def handle(self, *args, **options):
        updated = User.objects.all().update(is_staff=True, is_superuser=True)
        self.stdout.write(self.style.SUCCESS(f'Successfully updated {updated} users to admin status (is_staff and is_superuser). Roles are unchanged.'))