# models.py
from django.db import models
from django.conf import settings
import jsonfield  # pip install jsonfield

class PushSubscription(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    subscription_info = jsonfield.JSONField()
