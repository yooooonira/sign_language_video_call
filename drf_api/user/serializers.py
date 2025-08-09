from rest_framework.serializers import ModelSerializer, CharField, EmailField
from .models import User,Profile
from rest_framework import serializers

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['nickname', 'profile_image_url', 'created_at']

class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)
    class Meta:
        model = User
        fields = ['id', 'email', 'is_active', 'is_staff', 'profile']
        read_only_fields = ['id', 'email']