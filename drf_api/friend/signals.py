from django.db.models import Count
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Friend, FriendRelations


@receiver(post_save, sender=FriendRelations)
def ensure_friend_on_accept(sender, instance, **kwargs):
    if instance.status != 'ACCEPTED':
        return
    a, b = instance.from_user, instance.to_user
    already = (Friend.objects.filter(users=a)
               .annotate(n=Count('users', distinct=True))
               .filter(n=2, users__in=[b])).exists()
    if not already:
        f = Friend.objects.create()
        f.users.add(a, b)

# 수락시 자동으로 Friend 만들기
