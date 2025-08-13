from django.db import transaction
from django.db.models import Count, Exists, OuterRef
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import FriendRelations, Friend
from .serializers import FriendListSerializer,FriendDetailSerializer,ReceivedRequestSerializer,SentRequestSerializer,FriendRequestCreateSerializer,FriendRequestDetailSerializer
from .pagination import DefaultPagination
from rest_framework.exceptions import NotFound
from django.contrib.auth import get_user_model

User = get_user_model()

class AuthOnly(permissions.IsAuthenticated): # 로그인 한 사용자만 사용 가능
    pass

class FriendListView(generics.ListAPIView): #친구 목록 조회 
    permission_classes = [AuthOnly]
    serializer_class = FriendListSerializer
    pagination_class = DefaultPagination

    def get_queryset(self):
        me = self.request.user   #me : 현재 요청자 

        # 내가 포함된 Friend 중 정확히 2명으로 이루어진 행만 선택
        return (
            Friend.objects      
            .filter(users=me) #나를 기준으로
            .annotate(cnt=Count('users', distinct=True))  #각 friend의 사용자 수 
            .filter(cnt=2) #사용자 수가 2면 
            .prefetch_related('users__profile')   # 프로필(닉넴,프사,이멜)에 가져옴
            .order_by('-created_at')
        )



class FriendDetailDeleteView(generics.RetrieveDestroyAPIView):      #친구 프로필 조회, 친구 삭제
    permission_classes = [AuthOnly]
    serializer_class = FriendDetailSerializer 
    def get_object(self):
        me = self.request.user
        other_user_id = self.kwargs["pk"]  # /api/friends/<user_id>/
        friend = (
            Friend.objects
            .filter(users=me)
            .filter(users__id=other_user_id)
            .annotate(cnt=Count("users", distinct=True))
            .filter(cnt=2)  # 정확히 두 명인 친구쌍만
            .prefetch_related("users__profile")
            .order_by('-created_at')
            .first()
        )
        if not friend:
            raise NotFound(detail="친구가 아닙니다.", code="404_FRIEND_NOT_FOUND")
        return friend




class ReceivedRequestListView(generics.ListAPIView): #친추 받은 목록 조회 
    permission_classes = [AuthOnly]
    serializer_class = ReceivedRequestSerializer
    pagination_class = DefaultPagination

    def get_queryset(self):
        return (FriendRelations.objects     #friendrelation (친구관계)모델에서 
                .filter(to_user=self.request.user, status='PENDING') #수신자가 나일때 status가 pending이면 
                .select_related('from_user__profile') #발송자에 대한 정보를 가져와
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


#Post니까 generics.CreateAPIView
class FriendRequestCreateView(generics.CreateAPIView): #친구 추가
    permission_classes = [AuthOnly]
    serializer_class = FriendRequestCreateSerializer #요청값에 대한 시리얼라이저

    #CreateAPIView는 create()메서드를 오버라이드 
    def create(self, request, *args, **kwargs):
        # 입력 검증 & 저장 (입력용)
        serializer = self.get_serializer(data=request.data) #get_serializer()는 serializer_class에서 설정한 시리얼라이저를 자동으로 사용.
        #입력된(요청된)데이터를 FriendRequestCreateSerializer에 넣어서 인스턴스 생성한게 serializer
        serializer.is_valid(raise_exception=True) #그 요청된게 타당하면 
        instance = serializer.save()  #저장한다. 

        # 응답용
        out = FriendRequestDetailSerializer( #응답을 위한 시리얼라이즈
            instance,
            context=self.get_serializer_context()
            )
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
