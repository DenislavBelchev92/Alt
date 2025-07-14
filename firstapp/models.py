from django.contrib.auth.models import AbstractUser
from django.db import models

class AltUser(AbstractUser):
    sur_name = models.CharField(max_length=100, blank=True)
    age = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    
    def get_skills(self):
        return self.skill.all()
    
class Skill(models.Model):
    name = models.CharField(max_length=50, choices=[
        ('swimming', 'Swimming'),
        ('running', 'Running'),
        ('cycling', 'Cycling'),
        # Add more skills as needed
    ])
    user = models.ForeignKey(AltUser, on_delete=models.CASCADE, related_name='skill')
    rate = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        # Ensure swimming is always between 0 and 100
        self.rate = min(max(self.rate, 0), 100)
        super().save(*args, **kwargs)