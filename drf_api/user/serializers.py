from rest_framework.serializers import ModelSerializer, CharField, EmailField
from .models import User,Profile
from friend.models import Friend, FriendRelations
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
        fields = ["id", "email", "profile","is_staff","is_active"]


class UserSearchSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)
    is_friend = serializers.SerializerMethodField()
    friend_request_status = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "profile", "is_friend", "friend_request_status"]

    def get_is_friend(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        # 친구 여부 확인
        return Friend.objects.filter(users=request.user).filter(users=obj).exists()

    def get_friend_request_status(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None

        # 보낸 요청
        sent = FriendRelations.objects.filter(from_user=request.user, to_user=obj, status="PENDING").exists()
        if sent:
            return "PENDING_SENT"

        # 받은 요청
        received = FriendRelations.objects.filter(from_user=obj, to_user=request.user, status="PENDING").exists()
        if received:
            return "PENDING_RECEIVED"

        return None
