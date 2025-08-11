import hashlib
import random


def generate_unique_username():
    from user.models import Profile
    while True:
        username = hashlib.md5(str(random.random()).encode()).hexdigest()[:8]
        if not Profile.objects.filter(nickname=username).exists():
            return username
