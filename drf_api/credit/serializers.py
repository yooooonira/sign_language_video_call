from rest_framework import serializers
from .models import Credits

class CreditsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Credits
        fields = ["remained_credit", "last_updated", "last_used"]