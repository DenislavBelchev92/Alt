from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import AltUser, Profile, Skill

@receiver(post_save, sender=AltUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        # Create default profile for new users
        Profile.objects.create(user=instance)

@receiver(pre_save, sender=Skill)
def auto_populate_skill_metadata(sender, instance, **kwargs):
    """Automatically populate group and subgroup from the SkillName relationship"""
    if instance.name:
        instance.group = instance.name.subgroup.group.name
        instance.subgroup = instance.name.subgroup.name

@receiver(pre_save, sender=Skill)
def track_skill_changes(sender, instance, **kwargs):
    """Track when skill levels change"""
    if instance.pk:  # Only for existing skills being updated
        try:
            old_skill = Skill.objects.get(pk=instance.pk)
            if old_skill.level != instance.level:
                # You could add logging or history tracking here if needed
                pass
        except Skill.DoesNotExist:
            # New skill, no tracking needed
            pass
