from django.db import models
from django.conf import settings
from django.db.models import Q, F
from django.db.models.functions import Least, Greatest


class FriendRelations(models.Model):  # 친추 T
    from_user = models.ForeignKey(settings.AUTH_USER_MODEL,
                                  related_name='friend_requests_sent',
                                  on_delete=models.CASCADE)
    to_user = models.ForeignKey(settings.AUTH_USER_MODEL,
                                related_name='friend_requests_received',
                                on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=[
            ('PENDING', '보낸 요청'),
            ('ACCEPTED', '수락됨'),
            ('REJECTED', '거절됨')
        ])

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['from_user', 'to_user'],
                condition=Q(status='PENDING'),
                name='uniq_pending_per_direction',
            ),
            models.UniqueConstraint(
                Least(F('from_user'), F('to_user')),
                Greatest(F('from_user'), F('to_user')),
                condition=Q(status='PENDING'),
                name='uniq_pending_any_direction_v2',
            ),
        ]


class Friend(models.Model):  # 친구 관계 T
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='friend')
    created_at = models.DateTimeField(auto_now_add=True)
    pair_key = models.CharField(max_length=64, null=True, blank=True, db_index=True)
