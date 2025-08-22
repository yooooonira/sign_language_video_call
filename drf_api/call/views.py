
from .pagination import DefaultPagination
from rest_framework import generics
from rest_framework.views import APIView
from .models import CallHistory
from .serializers import CallHistoryListSerializer, CallHistoryDetailSerializer, CallHistoryRecordSerializer
from django.db.models import Q
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import AuthenticationFailed
import uuid
from rest_framework.response import Response
from django.contrib.auth import get_user_model
import asyncio
from .utils import notify_user

User = get_user_model()


class CallHistoryListView(generics.ListAPIView):  # 통화 기록 목록 조회 get
    pagination_class = DefaultPagination
    serializer_class = CallHistoryListSerializer

    def get_queryset(self):
        user = self.request.user

        if not user.is_active:
            raise PermissionDenied("비활성화된 계정입니다.")

        qs = (
            CallHistory.objects
            .filter(Q(caller=user) | Q(receiver=user))
            .select_related("caller", "receiver", "caller__profile", "receiver__profile")
            .order_by("-called_at")
            )
        return qs


class CallHistoryDetailView(generics.RetrieveDestroyAPIView):  # 특정 기록 조회get 삭제delete
    serializer_class = CallHistoryDetailSerializer

    def get_queryset(self):
        user = self.request.user

        return (
            CallHistory.objects
            .filter(Q(caller=user) | Q(receiver=user))
            .select_related("caller", "receiver", "caller__profile", "receiver__profile")
            )


class CallHistoryRecordView(generics.CreateAPIView):  # 통화 정보 기록 post
    serializer_class = CallHistoryRecordSerializer

    def perform_create(self, serializer):
        user = self.request.user
        if not user.is_authenticated:
            raise AuthenticationFailed("인증이 필요합니다.")
        serializer.save()  # caller는 serializer.create에서 request.user로 강제


from asgiref.sync import async_to_sync

class CallRequestView(APIView):
    def post(self, request):
        rid = request.data.get("receiver_id")
        room_id = uuid.uuid4().hex[:22]
        caller_id = request.user.id
        receiver_id = int(rid)

        # 안전하게 동기에서 호출
        async_to_sync(notify_user)(
            user_id=str(receiver_id),
            from_user=str(caller_id),
            room_id=room_id
        )

        return Response({
            "room_id": room_id,
            "caller_id": caller_id,
            "receiver_id": receiver_id
        }, status=201)
