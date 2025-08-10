from rest_framework.serializers import ModelSerializer, CharField, EmailField
from .models import User,Profile
from rest_framework import serializers

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['nickname', 'profile_image_url', 'created_at']
    def validate_nickname(self, value):
        user = self.context['request'].user
        if Profile.objects.filter(nickname=value).exclude(user=user).exists():
            raise serializers.ValidationError("이미 사용 중인 닉네임입니다.")
        return value
class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)
    class Meta:
        model = User
        fields = ['id', 'email', 'is_active', 'is_staff', 'profile']
        read_only_fields = ['id', 'email']