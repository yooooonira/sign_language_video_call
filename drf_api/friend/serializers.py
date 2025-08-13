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
    # profile = ProfileSerializer(read_only=True)
    profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'profile']
    
    def get_profile(self, obj):
        # related_name이 'profile'이 아닐 수도 있으니 getattr로 안정 접근
        p = getattr(obj, 'profile', None)
        return ProfileSerializer(p).data if p else None


class FriendListSerializer(serializers.ModelSerializer): # 친구 목록 조회 (친구 -> 유저 -> 프로필)
    other = serializers.SerializerMethodField()

    class Meta:
        model = Friend
        fields = ['id', 'other', 'created_at']

    def _get_other_user(self, obj):
        me = self.context['request'].user
        me_id = getattr(me, 'id', None)
        # 내 자신을 제외한 
        for u in obj.users.all():
            if u.id != me_id:
                return u
        return None

    def get_other(self, obj):
        other = self._get_other_user(obj)
        return UserSimpleSerializer(other, context=self.context).data if other else None
        
    

class FriendDetailSerializer(FriendListSerializer): # 친구 프로필 조회 
    friends_since = serializers.DateTimeField(source='created_at', format='%Y-%m-%d')

    class Meta(FriendListSerializer.Meta):
        fields = FriendListSerializer.Meta.fields + ['friends_since']


class ReceivedRequestSerializer(serializers.ModelSerializer): #친추 받은 목록
    from_user = UserSimpleSerializer(read_only=True)

    class Meta:
        model = FriendRelations
        fields = ["id", "from_user", "status"]

class SentRequestSerializer(serializers.ModelSerializer): #친추 보낸 목록
    to_user = UserSimpleSerializer(read_only=True)

    class Meta:
        model = FriendRelations
        fields = ["id", "to_user", "status"]

class FriendRequestCreateSerializer(serializers.ModelSerializer): #친구 추가
    to_user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())   #to_user:8 --> 8user에서 친구추가 

    class Meta:
        model = FriendRelations
        fields = ["to_user"]

    def validate_to_user(self, to_user):
        me = self.context['request'].user
        if me == to_user:
            raise serializers.ValidationError("자기 자신에게는 친구 요청을 보낼 수 없습니다.")
        return to_user

    def validate(self, attrs):
        me = self.context['request'].user
        to_user = attrs['to_user']

        # 이미 친구인지
        if Friend.objects.filter(users=me).filter(users=to_user).annotate(cnt=Count('users')).filter(cnt=2).exists():
            raise serializers.ValidationError("이미 친구입니다.")

        # 내가 이미 보낸 요청
        if FriendRelations.objects.filter(from_user=me, to_user=to_user, status='PENDING').exists():
            raise serializers.ValidationError("이미 친구 추가를 보냈습니다.")

        # 상대방이 이미 보낸 요청
        if FriendRelations.objects.filter(from_user=to_user, to_user=me, status='PENDING').exists():
            raise serializers.ValidationError("상대방이 이미 친구 요청을 보냈습니다.")

        return attrs

    def create(self, validated_data):
        me = self.context['request'].user
        return FriendRelations.objects.create(
            from_user=me,
            to_user=validated_data['to_user'],
            status='PENDING'
        )
class FriendRequestDetailSerializer(serializers.ModelSerializer): #친구 추가 (응답용)
    from_user = UserSimpleSerializer(read_only=True)
    to_user = UserSimpleSerializer(read_only=True)

    class Meta:
        model = FriendRelations
        fields = ["id", "from_user", "to_user", "status"] 