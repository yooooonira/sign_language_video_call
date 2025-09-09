import jsonfield  # pip install jsonfield
from django.conf import settings
from django.db import models


class PushSubscription(models.Model):
    user: models.OneToOneField = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    subscription_info: jsonfield.JSONCharField = jsonfield.JSONField()
