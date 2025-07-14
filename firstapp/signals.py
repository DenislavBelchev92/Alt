from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import AltUser, Skill, SkillName, SkillSubgroup, SkillGroup

@receiver(post_save, sender=AltUser)
def create_user_skills(sender, instance, created, **kwargs):
    if created:
        # Fetch or create SkillGroup
        group_obj, _ = SkillGroup.objects.get_or_create(name="Physics")

        # Fetch or create SkillSubgroup
        subgroup_obj, _ = SkillSubgroup.objects.get_or_create(name="Sport", group=group_obj)

        # Fetch or create SkillName
        skillname_obj, _ = SkillName.objects.get_or_create(name="Running", subgroup=subgroup_obj)

        # Finally, assign the skill to the user
        Skill.objects.create(user=instance, name=skillname_obj, level=10)
