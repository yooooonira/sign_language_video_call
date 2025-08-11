from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils.dateparse import parse_datetime

from .models import CallHistory
from .serializers import CallHistorySerializer
from .permissions import IsCallerOrReceiver

from django.utils import timezone
from rest_framework.exceptions import ValidationError

class CallHistoryViewSet(viewsets.ModelViewSet):
    queryset = CallHistory.objects.all().select_related('caller', 'receiver')
    serializer_class = CallHistorySerializer
    permission_classes = [IsAuthenticated]

    def _aware(dt_str: str, field: str):
        dt = parse_datetime(dt_str)
        if not dt:
            raise ValidationError({field: "ISO8601 형식이어야 합니다. 예) 2025-08-08T12:00:00Z"})
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_default_timezone())
        return dt
    # 목록: 내 통화만 + 필터
    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset().filter(Q(caller=user) | Q(receiver=user))

        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(call_status=status_param)

        # 기간 필터 (UTC ISO8601 문자열 기대)
        date_from = self.request.query_params.get('date_from')
        date_to   = self.request.query_params.get('date_to')
        
        if date_from:
                qs = qs.filter(started_at__gte=_aware(date_from, "date_from"))
        if date_to:
            qs = qs.filter(ended_at__lte=_aware(date_to, "date_to"))


        # 상대 사용자로 필터 (peer=<user_id>)
        peer = self.request.query_params.get('peer')
        if peer:
            qs = qs.filter(Q(caller_id=peer) | Q(receiver_id=peer))

        return qs

    # 객체 권한
    def get_permissions(self):
        if self.action in ['retrieve', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsCallerOrReceiver()]
        return [IsAuthenticated()]

    # 기본 create는 쓰지 않고 record 액션을 사용하게 유도
    def create(self, request, *args, **kwargs):
        return Response(
            {"detail": "이 엔드포인트 대신 POST /api/calls/record/ 를 사용하세요."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    @action(detail=False, methods=['post'], url_path='record')
    def record(self, request):
        data = request.data.copy()
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(caller=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)