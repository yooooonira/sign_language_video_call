from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Notification
from .serializers import NotificationListSerializer, NotificationDetailSerializer

class AuthOnly(permissions.IsAuthenticated):
    pass


class NotificationListView(generics.GenericAPIView):    #알림 목록 조회/삭제 (get, delete) (generic-> pageX)
    permission_classes = [AuthOnly]
    serializer_class = NotificationListSerializer

    def get_queryset(self):
        qs = (Notification.objects.filter(user=self.request.user).select_related("from_user", "from_user__profile").order_by("-created_at"))
        is_read = self.request.query_params.get("is_read")
        if is_read in ("true", "false"):
            qs = qs.filter(is_read=(is_read == "true"))

        ntype = self.request.query_params.get("type")
        if ntype:
            qs = qs.filter(notification_type=ntype)
        return qs

    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)  # settings.py의 DEFAULT_PAGINATION_CLASS 사용
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def delete(self, request, *args, **kwargs): #알림 전체 삭제
        deleted, _ = (Notification.objects.filter(user=request.user).delete())
        return Response({"deleted": deleted}, status=status.HTTP_200_OK)


class NotificationDetailView(generics.RetrieveDestroyAPIView):   #특정 알림 조회/삭제 
    permission_classes = [AuthOnly]
    serializer_class = NotificationDetailSerializer

    def get_queryset(self):
        return (Notification.objects.filter(user=self.request.user).select_related("from_user", "from_user__profile"))



class NotificationReadView(APIView):        #특정 알림 읽음 처리
    permission_classes = [AuthOnly]

    def patch(self, request, pk):
        try:
            obj = Notification.objects.get(pk=pk, user=request.user)
        except Notification.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if not obj.is_read:
            obj.is_read = True
            obj.save(update_fields=["is_read"])

        data = NotificationDetailSerializer(obj).data
        return Response(data, status=status.HTTP_200_OK)


class NotificationReadAllView(APIView):     #전체 알림 읽음 처리 
    permission_classes = [AuthOnly]

    def patch(self, request):
        qs = Notification.objects.filter(user=request.user, is_read=False)
        updated = qs.update(is_read=True)  
        return Response({"updated": updated}, status=status.HTTP_200_OK)
