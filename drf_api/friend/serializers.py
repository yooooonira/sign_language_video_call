from rest_framework import serializers
from django.contrib.auth import get_user_model     #user/mmodels.py
from django.db.models import Count # 중복 친구쌍 대비
from .models import FriendRelations, Friend
from user.models import Profile

User = get_user_model()

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['nickname', 'profile_image_url']

class UserSimpleSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'profile']


# class FriendSerializer(serializers.ModelSerializer):  #친구 프로필 조회
#     other = serializers.SerializerMethodField()

#     class Meta:
#         model = Friend
#         fields = ['id', 'other', 'created_at']

#     def get_other(self, obj):
#         me = self.context['request'].user
#         others = obj.users.exclude(id=me.id)
#         # 안전하게 첫번째만
#         return UserSimpleSerializer(others.first()).data if others.exists() else None

class FriendListSerializer(serializers.ModelSerializer): # 친구 목록 조회 (친구 -> 유저 -> 프로필)
    profile_image_url = serializers.SerializerMethodField()
    nickname = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
   
    class Meta:
        model = Friend
        fields = [ 'profile_image_url', 'nickname', 'email'] 
    def _get_other_user(self, obj):
        me = self.context['request'].user
        # 내 자신을 제외한 
        return obj.users.exclude(id=me.id).select_related('profile').first()

    def get_profile_image_url(self, obj):
        return self._get_other_user(obj).profile.profile_image_url
    def get_nickname(self, obj):
        return self._get_other_user(obj).profile.nickname
    def get_email(self, obj):
        return self._get_other_user(obj).email
    

class FriendDetailSerializer(FriendListSerializer): # 친구 프로필 조회 
    friends_since = serializers.DateTimeField(source='created_at', format='%Y-%m-%d')

    class Meta(FriendListSerializer.Meta):
        fields = FriendListSerializer.Meta.fields + ['friends_since']

    def get_user_id(self, obj):
        return self._get_other_user(obj).id


class FriendRequestSerializer(serializers.ModelSerializer): # 친추 밪은 목록, 친구 보낸 목록, 친구 추가 
    from_user = UserSimpleSerializer(read_only=True)
    to_user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), write_only=True)

    class Meta:
        model = FriendRelations
        fields = ['id', 'from_user', 'to_user', 'status']
        read_only_fields = ['id', 'from_user', 'status']

    def validate_to_user(self, to_user):
        me = self.context['request'].user
        if me == to_user:
            raise serializers.ValidationError("자기 자신에게는 친구 요청을 보낼 수 없습니다.")
        return to_user

    def validate(self, attrs):
        me = self.context['request'].user
        to_user = attrs['to_user']

        # 이미 친구인지 (기존 Friend 구조 그대로 사용)
        dup = (Friend.objects.filter(users=me).filter(users=to_user).annotate(cnt=Count('users')).filter(cnt=2).exists())
        if dup:
            raise serializers.ValidationError({"detail": "이미 친구입니다.", "code": "409_ALREADY_FRIEND"})

        # 내가 이미 보낸 친추
        if FriendRelations.objects.filter(from_user=me, to_user=to_user, status='PENDING').exists():
            raise serializers.ValidationError({"detail": "이미 친구 추가를 보냈습니다.", "code": "409_DUP_REQUEST"})

        # 상대가 이미 보낸 친추
        if FriendRelations.objects.filter(from_user=to_user, to_user=me, status='PENDING').exists():
            raise serializers.ValidationError({"detail": "이미 상대방이 친구추가를 보냈습니다.", "code": "409_OPPOSITE_PENDING"})

        return attrs

    def create(self, validated_data):
        me = self.context['request'].user
        return FriendRelations.objects.create(from_user=me, to_user=validated_data['to_user'], status='PENDING')
