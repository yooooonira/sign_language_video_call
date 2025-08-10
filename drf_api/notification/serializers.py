from rest_framework import serializers
from .models import Notification
from django.contrib.auth import get_user_model

User = get_user_model()


class FromUserSerializer(serializers.ModelSerializer):
    nickname = serializers.SerializerMethodField()
    profile_image_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "nickname", "profile_image_url")

    def get_nickname(self, obj):
        p = getattr(obj, "profile", None)
        return getattr(p, "nickname", None)

    def get_profile_image_url(self, obj):
        p = getattr(obj, "profile", None)
        return getattr(p, "profile_image_url", None)


class FromUserDetailSerializer(FromUserSerializer):  
    email = serializers.EmailField(source="email") 

    class Meta(FromUserSerializer.Meta):
        fields = ("id", "email", "nickname", "profile_image_url")


class NotificationListSerializer(serializers.ModelSerializer):  #알림 목록 조회
    from_user = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = (
            "id",
            "notification_type",
            "title",
            "is_read",
            "created_at",
            "from_user",
        )

    def get_from_user(self, obj):
        if obj.from_user_id is None:
            return None
        return FromUserSerializer(obj.from_user).data


class NotificationDetailSerializer(NotificationListSerializer):  #특정 알림 조회
    from_user = serializers.SerializerMethodField()

    class Meta(NotificationListSerializer.Meta):
        fields = NotificationListSerializer.Meta.fields   

    def get_from_user(self, obj):
        if obj.from_user_id is None:
            return None
        return FromUserDetailSerializer(obj.from_user).data