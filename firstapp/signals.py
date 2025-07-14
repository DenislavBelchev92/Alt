from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import AltUser, Skill

@receiver(post_save, sender=AltUser)
def create_user_skills(sender, instance, created, **kwargs):
    if created:
        Skill.objects.create(user=instance, name='running', rate=10)