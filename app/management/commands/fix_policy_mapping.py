from django.core.management.base import BaseCommand
from app.models import User, Policy
from django.db import transaction

class Command(BaseCommand):
    help = 'Ensures every user has exactly one Policy, and removes duplicates.'

    def handle(self, *args, **options):
        users = User.objects.all()
        fixed = 0
        for user in users:
            policies = Policy.objects.filter(user=user)
            if policies.count() == 0:
                Policy.objects.create(user=user)
                self.stdout.write(self.style.SUCCESS(f'Created Policy for user {user.username}'))
                fixed += 1
            elif policies.count() > 1:
                # Keep the first, delete the rest
                to_keep = policies.first()
                to_delete = policies.exclude(id=to_keep.id)
                to_delete.delete()
                self.stdout.write(self.style.WARNING(f'Removed duplicate Policies for user {user.username}'))
                fixed += 1
        self.stdout.write(self.style.SUCCESS(f'Policy cleanup complete. {fixed} users fixed.'))
