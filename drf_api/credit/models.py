from django.conf import settings
from django.db import models


class Credits(models.Model):
    user: models.OneToOneField = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="credits"
    )
    remained_credit: models.PositiveIntegerField = models.PositiveIntegerField(
        default=5
    )
    last_updated: models.DateTimeField = models.DateTimeField(auto_now=True)
    last_used: models.DateTimeField = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Credit"
        verbose_name_plural = "Credits"

    def __str__(self) -> str:
        return f"{self.user.email} - {self.remained_credit} credits"
