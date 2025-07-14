from django.contrib.auth.models import AbstractUser
from django.db import models

class AltUser(AbstractUser):
    sur_name = models.CharField(max_length=100, blank=True)
    age = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    
    def get_skills(self):
        grouped = {}
        for skill in self.skill.all():
            group = skill.name.subgroup.group.name
            subgroup = skill.name.subgroup.name
            if group not in grouped:
                grouped[group] = {}
            if subgroup not in grouped[group]:
                grouped[group][subgroup] = []
            grouped[group][subgroup].append(skill)
        return grouped
class SkillGroup(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class SkillSubgroup(models.Model):
    group = models.ForeignKey(SkillGroup, on_delete=models.CASCADE, related_name='skill_subgroups')
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name}"

class SkillName(models.Model):
    subgroup = models.ForeignKey(SkillSubgroup, on_delete=models.CASCADE, related_name='skill_names')
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name}"

class Skill(models.Model):
    name = models.ForeignKey(SkillName, on_delete=models.CASCADE)
    group = models.CharField(max_length=50, default="Unknown")
    subgroup = models.CharField(max_length=50, default="Unknown")
    user = models.ForeignKey(AltUser, on_delete=models.CASCADE, related_name='skill')
    level = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        # Ensure swimming is always between 0 and 100
        self.level = min(max(self.level, 0), 100)
        super().save(*args, **kwargs)