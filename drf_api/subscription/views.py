# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import PushSubscription
import json


class SaveSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # 클라이언트에서 받은 subscription_info
        subscription_info = request.data.get("subscription")
        if not subscription_info:
            return Response({"error": "Missing subscription"}, status=400)

        # 유저와 연동해서 DB 저장
        PushSubscription.objects.update_or_create(
            user=request.user,
            defaults={"subscription_info": json.dumps(subscription_info)}
        )
        return Response({"status": "saved"})
