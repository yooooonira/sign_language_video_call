from rest_framework import serializers
from .models import CallHistory
from .services import calc_used_credits

class CallHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CallHistory
        fields = [
            'id', 'caller', 'receiver',
            'started_at', 'ended_at',
            'used_credits', 'call_status',
            'called_at'
        ]
        read_only_fields = ['caller', 'used_credits', 'called_at']

    def validate(self, attrs):
        receiver = attrs.get('receiver') or getattr(self.instance, 'receiver', None)
        caller = self.context['request'].user
        if receiver and caller and receiver.id == caller.id:
            raise serializers.ValidationError("caller와 receiver는 같을 수 없습니다.")

        started_at = attrs.get('started_at') or getattr(self.instance, 'started_at', None)
        ended_at   = attrs.get('ended_at')   or getattr(self.instance, 'ended_at', None)
        if started_at and ended_at and ended_at < started_at:
            raise serializers.ValidationError("ended_at은 started_at보다 빠를 수 없습니다.")
        return attrs

    def create(self, validated_data):
        started_at = validated_data.get('started_at')
        ended_at   = validated_data.get('ended_at')

        call = CallHistory(**validated_data)
        if started_at and ended_at:
            call.used_credits = calc_used_credits(started_at, ended_at)
        call.save()
        return call