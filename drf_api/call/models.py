from django.db import models
from django.conf import settings
class CallHistory(models.Model):
    CALL_STATUS_CHOICES = [
            ('ACCEPTED', '수락됨'),
            ('MISSED', '부재중'),
            ('REJECTED', '거절됨'),
        ]
    caller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,related_name='outgoing_calls')
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,related_name='incoming_calls')
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    used_credits = models.IntegerField(default=0)

    call_status = models.CharField(max_length=10, choices=CALL_STATUS_CHOICES)
    called_at   = models.DateTimeField(auto_now_add=True)