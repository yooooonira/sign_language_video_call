from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import CallHistory
from django.db.models.fields.files import FieldFile

User = get_user_model()


class CallHistoryListSerializer(serializers.ModelSerializer): #통화 목록
    caller = serializers.SerializerMethodField()
    receiver = serializers.SerializerMethodField()

    class Meta:
        model = CallHistory
        fields = ["id", "caller", "receiver", "called_at","started_at","ended_at","call_status"]


    def get_caller(self, obj):
        return {
            "id": obj.caller.id,
            "nickname": obj.caller.profile.nickname,
            "profile_image_url": obj.caller.profile.profile_image_url.url if obj.caller.profile.profile_image_url else None
        }

    def get_receiver(self, obj):
        return {
            "id": obj.receiver.id,
            "nickname": obj.receiver.profile.nickname,
            "profile_image_url": obj.receiver.profile.profile_image_url.url if obj.receiver.profile.profile_image_url else None
        }



class CallHistoryDetailSerializer(serializers.ModelSerializer): #특정 통화
    is_caller = serializers.SerializerMethodField()
    direction = serializers.SerializerMethodField()
    duration_seconds = serializers.SerializerMethodField()
    used_credits = serializers.SerializerMethodField()
    caller = serializers.SerializerMethodField()
    receiver = serializers.SerializerMethodField()

    class Meta:
        model = CallHistory
        fields = ["id","direction","caller","receiver","call_status","called_at", "duration_seconds",
            "used_credits","is_caller","started_at","ended_at",]
        read_only_fields = fields

    def _is_caller(self, obj):
        user = self.context["request"].user
        return obj.caller == user

    def get_is_caller(self, obj):    #누가 걸었냐 T/F
        return self._is_caller(obj)

    def get_direction(self, obj):
        return "OUTGOING" if self._is_caller(obj) else "INCOMING"

    def get_caller(self, obj):
        return {
            "id": obj.caller.id,
            "nickname": obj.caller.profile.nickname,
            "profile_image_url": obj.caller.profile.profile_image_url.url if obj.caller.profile.profile_image_url else None
        }

    def get_receiver(self, obj):
        return {
            "id": obj.receiver.id,
            "nickname": obj.receiver.profile.nickname,
            "profile_image_url":  obj.receiver.profile.profile_image_url.url if obj.receiver.profile.profile_image_url else None
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
        status = attrs.get("call_status")

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
        if status in {"MISSED", "REJECTED"}:
            attrs["started_at"] = None
            attrs["ended_at"] = None
        else:
            if (started_at is None) or (ended_at is None):
                raise serializers.ValidationError(
                    {"non_field_errors": "연결된 통화 상태에서는 started_at과 ended_at이 모두 필요합니다."}
                )
            if ended_at < started_at:
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