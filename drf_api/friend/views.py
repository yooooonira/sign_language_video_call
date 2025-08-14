from django.db import transaction
from django.db.models import Count, Max,Min, Q
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import FriendRelations, Friend
from .serializers import FriendListSerializer,FriendDetailSerializer,ReceivedRequestSerializer,SentRequestSerializer,FriendRequestCreateSerializer,FriendRequestDetailSerializer,FriendListSerializer
from django.shortcuts import get_object_or_404
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

        return (
            User.objects
            .filter(friend__users=me)
            .exclude(id=me.id)
            .select_related('profile')
            .annotate(
                cnt=Count('friend', distinct=True),
                last_friend_at=Max(
                    'friend__created_at',
                    filter=Q(friend__users=me)
                )
            )
            .distinct()
            .order_by('-last_friend_at')
            )



class FriendRetrieveDeleteView(generics.RetrieveDestroyAPIView):      #친구 프로필 조회, 친구 삭제
    permission_classes = [AuthOnly]
    serializer_class = FriendDetailSerializer 
    

    def get_object(self): #조회
        me = self.request.user
        other_id = self.kwargs.get("pk")  

        return(
            User.objects
            .filter(id=other_id, friend__users=me)  
            .select_related('profile')
            .annotate(
                created_at=Min('friend__created_at', filter=Q(friend__users=me))
            )
            .distinct()                              
            .first()                                
        )


        

    def destroy(self, request, *args, **kwargs):
        me = request.user
        other_id = self.kwargs.get("pk")  # URL pk

        Friend.objects.filter(users=me).filter(users__id=other_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)




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


class FriendRequestCreateView(generics.CreateAPIView): #친구 추가
    permission_classes = [AuthOnly]
    serializer_class = FriendRequestCreateSerializer 

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        me = request.user

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        to_user = serializer.validated_data["to_user"]

        # 내가 나한테
        if me.id == to_user.id:
            return Response({
                "outcome": "SELF_REQUEST",
                "state": "INVALID",
                "message": "자기 자신에게는 친구 요청을 보낼 수 없습니다."
            }, status=status.HTTP_200_OK)

        # 이미 친구 
        friend = (Friend.objects
                  .filter(users=me)          
                  .filter(users=to_user) 
                  .exists()
                )
        if friend:
            return Response({
                "outcome": "Already_friends",
                "state": "friends",
                "friend_id": friend.id
            }, status=status.HTTP_200_OK)

        # 상대가 이미 친구 보낸 상태 
        inbound = (FriendRelations.objects
                   .filter(from_user=to_user, to_user=me, status="PENDING")
                   .first()
                   )
        if inbound:
            return Response({
                "outcome":"Already_inbound",
                "state":"PENDING_inbound",
                "inbound_request_id": inbound.id,
                "message":"상대방이 이미 친구 요청을 보냈어요. 수락/거절하세요."
            }, status=status.HTTP_200_OK)
        
        # 내가 이미 친구 보낸 상태
        outbound = (FriendRelations.objects
            .filter(from_user=me, to_user=to_user, status="PENDING")
            .first()
            )
        if outbound:
            return Response({
                "outcome":"Already_outbound",
                "state":"PENDING_outbound",
                "outbound_request_id": outbound.id
            }, status=status.HTTP_200_OK)
        
        instance=serializer.save(from_user=me)

        out = FriendRequestDetailSerializer(
            instance,
            context=self.get_serializer_context()
            )
        headers = self.get_success_headers({"id": instance.pk})
       
        return Response({
            "outcome":"created",
            "state":"PENDING_outbound",
            "request": out.data
        }, status=status.HTTP_201_CREATED, headers=headers)
        
    


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
        exists = (Friend.objects.filter(users=me).filter(users=other).exists())
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


class FriendRequestDestroyView(generics.DestroyAPIView): # 친구 요청 취소 
    permission_classes = [AuthOnly]
    queryset = FriendRelations.objects.all()  # 안전하게 get_object에서 필터링

    def get_object(self):
        me = self.request.user
        other_id = self.kwargs["pk"]
        obj = (FriendRelations.objects
               .filter(id=other_id, status="PENDING", from_user=me)  #대기중만
               .first())
        if not obj:
            raise NotFound("취소할 보낸 요청이 없어요.")
        return obj