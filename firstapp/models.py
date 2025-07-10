from django.contrib.auth.models import AbstractUser
from django.db import models

class AltUser(AbstractUser):
    sur_name = models.CharField(max_length=100, blank=True)
    age = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)

class Skills(models.Model):
    user = models.OneToOneField(AltUser, on_delete=models.CASCADE, related_name='skills')
    city = models.CharField(max_length=100, blank=True)
    swimming = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        # Ensure swimming is always between 0 and 100
        self.swimming = min(max(self.swimming, 0), 100)
        super().save(*args, **kwargs)