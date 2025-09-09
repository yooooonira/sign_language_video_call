from django.test import TestCase
# from django.urls import reverse
from rest_framework.test import APIClient
# from rest_framework import status
# from unittest.mock import patch
from user.models import User, Profile


class UserProfileTestCase(TestCase):
    def setUp(self):
        """테스트 설정"""
        self.client = APIClient()
        self.email = "test@example.com"
        self.nickname = "testnickname"

        # 테스트용 JWT 토큰 모킹을 위한 사용자 정보
        self.mock_user_info = {
            "email": self.email,
            "nickname": self.nickname
        }

    def test_user_model_creation(self):
        """User 모델 생성 테스트"""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpassword123"
        )

        self.assertEqual(user.email, "test@example.com")
        self.assertTrue(user.check_password("testpassword123"))
        self.assertTrue(user.is_active)

    def test_profile_model_creation(self):
        """Profile 모델 생성 테스트"""
        user = User.objects.create_user(email="test@example.com")
        profile = Profile.objects.create(
            user=user,
            nickname="testnickname"
        )

        self.assertEqual(profile.user, user)
        self.assertEqual(profile.nickname, "testnickname")
        self.assertEqual(str(profile), "testnickname")
