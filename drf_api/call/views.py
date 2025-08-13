
from .pagination import DefaultPagination
from rest_framework import permissions,generics
from rest_framework.views import APIView
from .models import CallHistory
from .serializers import CallHistoryListSerializer,CallHistoryDetailSerializer,CallHistoryRecordSerializer
from django.db.models import Q
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import AuthenticationFailed

class AuthOnly(permissions.IsAuthenticated): # 로그인 한 사용자만 사용 가능
    pass

class CallHistoryListView(generics.ListAPIView): #통화 기록 목록 조회 get 
    permission_classes = [AuthOnly]
    pagination_class = DefaultPagination
    serializer_class = CallHistoryListSerializer

    def get_queryset(self):
        user = self.request.user

        if not user.is_active:
            raise PermissionDenied("비활성화된 계정입니다.")

        qs=(CallHistory.objects
            .filter(Q(caller=user) | Q(receiver=user))  
            .select_related("caller", "receiver", "caller__profile", "receiver__profile") 
            .order_by("-called_at")  
            )   
        return qs


class CallHistoryDetailView(generics.RetrieveAPIView): #특정 특정 기록 조회get
    permission_classes = [AuthOnly]
    serializer_class = CallHistoryDetailSerializer

    def get_queryset(self):
        user = self.request.user

        if not user.is_active:
            raise PermissionDenied("비활성화된 계정입니다.")

        qs=(CallHistory.objects
            .filter(Q(caller=user) | Q(receiver=user))
            .select_related("caller", "receiver", "caller__profile", "receiver__profile")
            )   
        return qs


class CallHistoryRecordView(generics.CreateAPIView): #통화 정보 기록 post
    permission_classes = [AuthOnly]
    serializer_class = CallHistoryRecordSerializer

    def perform_create(self, serializer):
        user = self.request.user
        if not user.is_authenticated:
            raise AuthenticationFailed("인증이 필요합니다.")
        serializer.save()  
