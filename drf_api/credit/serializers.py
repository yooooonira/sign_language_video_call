from rest_framework import serializers
from .models import Credits

class CreditsSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True) # read_only=True : 수정불가, API 응답 전용
    class Meta:
        model = Credits
        fields = ["user_email", "remained_credit", "last_updated", "last_used"]