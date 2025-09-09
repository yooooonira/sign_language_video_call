from django.conf import settings
from django.db import models


class Notification(models.Model):
    NOTIFICATION_TYPES = [
            ('FRIEND_REQUEST', '친구 요청'),
            ('FRIEND_ACCEPTED', '친구 수락'),
            ('FRIEND_REJECTED', '친구 거절'),
            ('CALL_INCOMING', '전화 요청 옴'),
            ('CALL_REJECTED', '전화 거절됨'),
            ('CALL_MISSED', '부재중 전화'),
            ('CREDIT_LOW', '크레딧 부족'),
            ('SYSTEM', '시스템 안내'),
        ]
    user: models.ForeignKey = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    from_user: models.ForeignKey = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                                     null=True, blank=True, related_name='sent_notifications')
    title: models.CharField = models.CharField(max_length=100)
    notification_type: models.CharField = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    is_read: models.BooleanField = models.BooleanField(default=False)
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"{self.user.username}: {self.title} ({self.notification_type})"
