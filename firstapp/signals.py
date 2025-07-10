from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import AltUser, Skills

@receiver(post_save, sender=AltUser)
def create_user_skills(sender, instance, created, **kwargs):
    if created:
        Skills.objects.create(user=instance)  # This will use the default values