from rest_framework import serializers
from django.contrib.auth import get_user_model 
from .models import CallHistory
from django.db.models.fields.files import FieldFile

User = get_user_model()


class CallHistoryListSerializer(serializers.ModelSerializer): #통화 목록
    call_id = serializers.IntegerField(source="id", read_only=True) 
    peer = serializers.SerializerMethodField()
    class Meta:
        model = CallHistory
        fields = [
            "call_id",
            "peer",
            "called_at",
        ]
    def get_peer(self, obj):
        user = self.context["request"].user 
        peer_user = obj.receiver if obj.caller == user else obj.caller 
        profile = getattr(peer_user, "profile", None)
        request = self.context.get("request")

        img = getattr(profile, "profile_image_url", None)
        img_url = None
        if isinstance(img, FieldFile) and img:  
            img_url = img.url
        elif isinstance(img, str) and img:               
            img_url = img

        if img_url and request and img_url.startswith("/"):
            img_url = request.build_absolute_uri(img_url) 

        return { 
            "user_id": getattr(peer_user, "id", None),
            "nickname": getattr(peer_user.profile, "nickname", None),
            "profile_image_url": img_url,
        }
            
class CallHistoryDetailSerializer(serializers.ModelSerializer): #특정 통화 
    is_caller = serializers.SerializerMethodField()
    direction = serializers.SerializerMethodField()     
    peer = serializers.SerializerMethodField()
    duration_seconds = serializers.SerializerMethodField()
    used_credits = serializers.SerializerMethodField()
    class Meta:
        model = CallHistory
        fields = [
            "id",
            "direction",
            "peer",
            "call_status",
            "called_at",
            "duration_seconds",
            "used_credits",
            "is_caller",
        ]
        read_only_fields = fields

    def _is_caller(self, obj): 
        user = self.context["request"].user
        return obj.caller == user 
    

    def get_is_caller(self, obj):
        return self._is_caller(obj)

    def get_direction(self, obj):
        return "OUTGOING" if self._is_caller(obj) else "INCOMING"

    def get_peer(self, obj):
            user = self.context["request"].user 
            peer_user = obj.receiver if obj.caller == user else obj.caller 
            profile = getattr(peer_user, "profile", None)
            request = self.context.get("request")
            
            img = getattr(profile, "profile_image_url", None)
            img_url = None
            if isinstance(img, FieldFile) and img:
                img_url = img.url
            elif isinstance(img, str) and img:
                img_url = img

            if img_url and request and img_url.startswith("/"):
                img_url = request.build_absolute_uri(img_url)


            return {
                "id": getattr(peer_user, "id", None),
                "nickname": getattr(peer_user.profile, "nickname", None),
                "profile_image_url":img_url,
            }

    def get_duration_seconds(self, obj):
        if obj.started_at and obj.ended_at:
            duration = obj.ended_at - obj.started_at
            return int(duration.total_seconds())
        return None

    def get_used_credits(self, obj):
        return obj.used_credits if self._is_caller(obj) else None
    


class CallHistoryRecordSerializer(serializers.ModelSerializer):  #통화 기록
    receiver_id = serializers.IntegerField(write_only=True) 
    id = serializers.IntegerField(read_only=True)
    called_at = serializers.DateTimeField(read_only=True) 

    class Meta:
        model = CallHistory
        fields = [
            "id",                           
            "receiver_id",                 
            "call_status",
            "started_at",
            "ended_at",
            "used_credits",
            "called_at",
        ]
        read_only_fields = ["id", "called_at"]

    def validate(self, attrs): 
        request = self.context["request"] 
        caller = request.user             

        try:
            receiver = User.objects.get(pk=attrs["receiver_id"])  
        except User.DoesNotExist:
            raise serializers.ValidationError({"receiver_id": "존재하지 않는 사용자입니다."})

        if receiver == caller:
            raise serializers.ValidationError({"receiver_id": "자기 자신에게는 통화할 수 없습니다."})

        valid_status = {c[0] for c in CallHistory.CALL_STATUS_CHOICES}
        if attrs.get("call_status") not in valid_status:
            raise serializers.ValidationError({"call_status": "허용되지 않는 상태입니다."})

        started_at = attrs.get("started_at")
        ended_at = attrs.get("ended_at")
        if started_at and ended_at and ended_at < started_at:
            raise serializers.ValidationError({"ended_at": "ended_at은 started_at 이후여야 합니다."})

        attrs["_receiver_obj"] = receiver
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        caller = request.user
        receiver = validated_data.pop("_receiver_obj") 
        validated_data.pop("receiver_id", None)         

        obj = CallHistory.objects.create(
            caller=caller,
            receiver=receiver,
            **validated_data
        )
        return obj