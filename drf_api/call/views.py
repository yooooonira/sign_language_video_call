
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
from .utils import notify_user_via_webpush
from subscription.models import PushSubscription
from django.utils import timezone
from django.shortcuts import get_object_or_404

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

# 통화 요청 뷰
class CallRequestView(APIView):
    def post(self, request):
        rid = request.data.get("receiver_id")
        room_id = uuid.uuid4().hex[:22]

        # CallHistory 저장 등 기존 로직

        # 푸시 알림
        caller = User.objects.get(id=request.user.id)  # me
        caller_name = getattr(caller.profile, "nickname", caller.email)  # profile.nickname
        subscription = PushSubscription.objects.get(user_id=rid)
        notify_user_via_webpush(subscription.subscription_info, request.user.id, caller_name, room_id)

        return Response({"room_id": room_id})

# 통화 거절 뷰
class CallRejectView(APIView):
    """
    상대방이 수락하지 않고 거절했을 때 호출
    """
    def post(self, request):
        room_id = request.data.get("room_id")
        caller_id = request.data.get("caller_id")
        receiver = request.user

        caller = get_object_or_404(User, id=caller_id)

        # CallHistory 생성 (started_at 없음)
        call = CallHistory.objects.create(
            caller=caller,
            receiver=receiver,
            call_status='REJECTED',
            room_id=room_id
        )

        return Response({"success": True, "call_id": call.id})

# 통화 수락 뷰
class CallAcceptView(APIView):
    """
    상대방이 통화를 수락했을 때 호출
    """
    def post(self, request):
        room_id = request.data.get("room_id")
        caller_id = request.data.get("caller_id")
        receiver = request.user

        caller = get_object_or_404(User, id=caller_id)

        # CallHistory 생성
        call = CallHistory.objects.create(
            caller=caller,
            receiver=receiver,
            call_status='ACCEPTED',
            started_at=timezone.now(),
            room_id=room_id
        )

        return Response({"success": True, "call_id": call.id})

# 통화 부재중 뷰
class CallMissedView(APIView):
    """
    통화가 걸렸지만 30초 동안 수락하지 않아 부재중 처리
    """
    def post(self, request):
        print("CallMissedView 호출됨")
        room_id = request.data.get("room_id")
        caller_id = request.data.get("caller_id")
        receiver = request.user

        caller = get_object_or_404(User, id=caller_id)

        call = CallHistory.objects.create(
            caller=caller,
            receiver=receiver,
            call_status='MISSED',
            room_id=room_id
        )

        return Response({"success": True, "call_id": call.id})




# 통화 종료 뷰
class CallEndView(APIView):
    def post(self, request):
        room_id = request.data.get("room_id")
        used_credits = request.data.get("used_credits", 0)
        try:
            call = CallHistory.objects.get(room_id=room_id)
            call.ended_at = timezone.now()
            call.used_credits = used_credits
            call.save()
            return Response({"success": True})
        except CallHistory.DoesNotExist:
            return Response({"error": "Call not found"}, status=404)
