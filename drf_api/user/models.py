from django.db import models
from django.contrib.auth.models import (
        AbstractBaseUser,
        PermissionsMixin,
        BaseUserManager
    )
import uuid
import os


def profile_image_file_path(instance, filename):
    ext = filename.split(".")[-1]
    filename = f"profile-{uuid.uuid4()}.{ext}"
    return os.path.join("uploads/profiles/", filename)


class UserManager(BaseUserManager):
    #사용자 생성 매니저
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("이메일은 필수입니다.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password):
        user = self.create_user(email=email, password=password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user
class User(AbstractBaseUser, PermissionsMixin):
    #사용자 모델
    email = models.EmailField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    objects = UserManager()

    USERNAME_FIELD = "email"

    def __str__(self):
        return self.email


class Profile(models.Model):
    #프로필 모델
    user = models.OneToOneField(
            User,
            on_delete=models.CASCADE,
            related_name="profile"
        )
    nickname = models.CharField(max_length=50, unique=True, null=True)
    profile_image_url = models.ImageField(null=True, blank=True, upload_to=profile_image_file_path)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.nickname or f"Profile of {self.user.email}"
