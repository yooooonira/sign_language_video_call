from django.db import models
from django.conf import settings


class FriendRelations(models.Model): # 친추 T
    from_user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='friend_requests_sent',on_delete=models.CASCADE)
    to_user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='friend_requests_received',on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=[
            ('PENDING', '보낸 요청'),
            ('ACCEPTED', '수락됨'),
            ('REJECTED', '거절됨')
        ])
    class Meta:
        unique_together = ('from_user', 'to_user')

class Friend(models.Model): # 친구 관계 T
    users = models.ManyToManyField(settings.AUTH_USER_MODEL)
    created_at = models.DateTimeField(auto_now_add=True)

