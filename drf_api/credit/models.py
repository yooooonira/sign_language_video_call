from django.db import models
from django.conf import settings

class Credits(models.Model):
 user = models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE, related_name="credits")
 remained_credit = models.PositiveIntegerField(default=5)
 last_updated = models.DateTimeField(auto_now=True)
 last_used = models.DateTimeField(null=True, blank=True)

class Meta:
        vervose_name = "Credit"
        verbose_name_plural = "Credits"

def __str__(self):
    return f"{self.user.username} - {self.remained_credit} credits"