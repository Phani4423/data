from django.db.models.signals import post_save
from django.dispatch import receiver
from app.models import User, Policy

@receiver(post_save, sender=User)
def create_user_policy(sender, instance, created, **kwargs):
    if created:
        Policy.objects.create(user=instance)
