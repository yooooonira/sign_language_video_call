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
    user_id = serializers.IntegerField(source="id")
    profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['user_id', 'email', 'profile']
    
    def get_profile(self, obj):
        # related_name이 'profile'이 아닐 수도 있으니 getattr로 안정 접근
        p = getattr(obj, 'profile', None)
        if p:
            return ProfileSerializer(p).data
        nickname = (obj.email.split("@")[0] if obj.email else "")
        return {
            "nickname": nickname,
            "profile_image_url": None,
        }


class FriendListSerializer(serializers.ModelSerializer): # 친구 목록 조회 (친구 -> 유저 -> 프로필)
    profile = ProfileSerializer(read_only=True)  # select_related('profile') 결과 사용
    cnt = serializers.IntegerField(read_only=True)  # annotate(cnt=...) 값 내려주기

    class Meta:
        model = User
        fields = ['id', 'email', 'profile', 'cnt']


      

class FriendDetailSerializer(FriendListSerializer): # 친구 프로필 조회 
    profile = ProfileSerializer(read_only=True)
    created_at = serializers.DateTimeField(read_only=True) 
    class Meta:
        model = User
        fields = ["id", "email", "profile","created_at"]



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
        fields = ["to_user","id","status"]
        read_only_fields = ["id","status"]

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