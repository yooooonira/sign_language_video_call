import os
import uuid
from typing import Any, Optional

from django.contrib.auth.models import (AbstractBaseUser, BaseUserManager,
                                        PermissionsMixin)
from django.db import models


def profile_image_file_path(instance: Any, filename: str) -> str:
    ext = filename.split(".")[-1]
    filename = f"profile-{uuid.uuid4()}.{ext}"
    return os.path.join("uploads/profiles/", filename)


class UserManager(BaseUserManager):
    # 사용자 생성 매니저
    def create_user(self, email: str, password: Optional[str] = None, **extra_fields: Any) -> 'User':
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

    def create_superuser(self, email: str, password: str) -> 'User':
        user = self.create_user(email=email, password=password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    # 사용자 모델
    email: models.EmailField = models.EmailField(max_length=255, unique=True)
    is_active: models.BooleanField = models.BooleanField(default=True)
    is_staff: models.BooleanField = models.BooleanField(default=False)
    objects = UserManager()

    USERNAME_FIELD = "email"

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self) -> str:
        return self.email


class Profile(models.Model):
    # 프로필 모델
    user: models.OneToOneField = models.OneToOneField(
            User,
            on_delete=models.CASCADE,
            related_name="profile"
        )
    nickname: models.CharField = models.CharField(max_length=50, unique=True, null=True)
    profile_image_url: models.ImageField = models.ImageField(null=True,
                                                             blank=True,
                                                             upload_to=profile_image_file_path)
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Profile"
        verbose_name_plural = "Profiles"

    def __str__(self) -> str:
        return self.nickname or f"Profile of {self.user.email}"
