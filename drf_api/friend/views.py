from django.db import transaction
from django.db.models import Count, Exists, OuterRef
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import FriendRelations, Friend
from .serializers import FriendListSerializer,FriendDetailSerializer,ReceivedRequestSerializer,SentRequestSerializer,FriendRequestCreateSerializer,FriendRequestDetailSerializer
from .pagination import DefaultPagination

class AuthOnly(permissions.IsAuthenticated): # 로그인 한 사용자만 사용 가능
    pass

class FriendListView(generics.ListAPIView):
    permission_classes = [AuthOnly]
    serializer_class = FriendListSerializer
    pagination_class = DefaultPagination

    def get_queryset(self):
        me = self.request.user
        me_in_friend = Friend.objects.filter(id=OuterRef('id'), users=me) #
        # return (
        #     Friend.objects
        #     .filter(users=me)
        #     .annotate(cnt=Count('users'))
        #     .filter(cnt=2)
        #     .prefetch_related('users__profile')
        #     .order_by('-created_at')
        #     .distinct()
        # )
        return (
            Friend.objects
            .annotate(total_users=Count('users', distinct=True),
                      has_me=Exists(me_in_friend))
            .filter(has_me=True, total_users=2)
            .prefetch_related('users__profile')
            .order_by('-id')
        )



class FriendDetailDeleteView(APIView):   #친구 프로필 조회, 친구 삭제
    permission_classes = [AuthOnly]

    def get(self, request, pk): #친구 프로필 조회
        me = request.user
        # 두 유저를 모두 포함하고 정확히 2명인 Friend 한 건
        friend = (Friend.objects.filter(users=me)
                  .filter(users__id=pk)
                  .annotate(cnt=Count('users'))
                  .filter(cnt=2)
                  .prefetch_related('users__profile').first())
        if not friend:
            return Response({"detail": "친구가 아닙니다.", "code": "404_FRIEND_NOT_FOUND"}, status=404)
        return Response(FriendDetailSerializer(friend, context={'request': request}).data, status=200)

    def delete(self, request, pk):#친구 삭제
        me = request.user
        friend = (Friend.objects
                  .filter(users=me)
                  .filter(users__id=pk)   #url의 id가 user_id
                  .annotate(cnt=Count('users'))
                  .filter(cnt=2))
        deleted, _ = friend.delete()
        if not deleted:
            return Response({"detail": "삭제 대상 친구 없음", "code": "404_FRIEND_NOT_FOUND"}, status=404)
        return Response(status=204)




class ReceivedRequestListView(generics.ListAPIView): #친추 받은 목록 조회 
    permission_classes = [AuthOnly]
    serializer_class = ReceivedRequestSerializer
    pagination_class = DefaultPagination

    def get_queryset(self):
        return (FriendRelations.objects
                .filter(to_user=self.request.user, status='PENDING')
                .select_related('from_user__profile')
                .order_by("-id"))

class SentRequestListView(generics.ListAPIView): #친추 보낸 목록 조회 
    permission_classes = [AuthOnly]
    serializer_class = SentRequestSerializer
    pagination_class = DefaultPagination

    def get_queryset(self):
        return (FriendRelations.objects
                .filter(from_user=self.request.user, status='PENDING')
                .select_related('to_user__profile')
                .order_by("-id") )

class FriendRequestCreateView(generics.CreateAPIView): #친구 추가
    permission_classes = [AuthOnly]
    serializer_class = FriendRequestCreateSerializer
    def create(self, request, *args, **kwargs):
        # 입력 검증 & 저장 (입력용)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()  # create()에서 from_user/me 설정됨

        # 출력 변환 (출력용)
        out = FriendRequestDetailSerializer(instance, context=self.get_serializer_context())
        headers = self.get_success_headers({"id": instance.pk})
        return Response(out.data, status=status.HTTP_201_CREATED, headers=headers)

class FriendRequestAcceptView(APIView): #친구 수락
    permission_classes = [AuthOnly]

    @transaction.atomic
    def post(self, request, pk):
        # 요청 행을 락으로 묶어 중복 생성 방지
        try:
            fr = (FriendRelations.objects.select_for_update().get(id=pk, to_user=request.user, status='PENDING'))
        except FriendRelations.DoesNotExist:
            return Response({"detail": "요청 없음", "code": "404_REQUEST_NOT_FOUND"}, status=404)

        me = fr.to_user
        other = fr.from_user

        # 이미 친구인지 다시 한 번 체크(동시성)
        exists = (Friend.objects.filter(users=me).filter(users=other).annotate(cnt=Count('users')).filter(cnt=2).exists())
        if not exists:
            # 없을 때만 새로 만들고 두 명 추가
            f = Friend.objects.create()
            f.users.add(me, other)

        fr.status = 'ACCEPTED'
        fr.save(update_fields=['status'])
        return Response({"message": "친구 수락 완료"}, status=200)

class FriendRequestRejectView(APIView):  #친구 거절
    permission_classes = [AuthOnly]

    def post(self, request, pk):
        updated = (FriendRelations.objects
                   .filter(id=pk, to_user=request.user, status='PENDING')
                   .update(status='REJECTED'))
        if not updated:
            return Response({"detail": "요청 없음", "code": "404_REQUEST_NOT_FOUND"}, status=404)
        return Response({"message": "친구 요청 거절됨"}, status=200)
