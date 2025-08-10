from rest_framework import generics, permissions,status,viewsets
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from core.utils.generate_name import generate_unique_username
from core.views import SupabaseJWTAuthentication
from rest_framework import status
from user.models import Profile
from credit.models import Credits
from .serializers import ProfileSerializer,UserSerializer
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

# 소셜 로그인/회원가입(profile)
class SocialSignupView(APIView):
    authentication_classes = [SupabaseJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        nickname = getattr(user, "nickname", None)
        if not user.email:
            return Response({"error": "Email not found in token"}, status=status.HTTP_400_BAD_REQUEST)

        profile_exists = Profile.objects.filter(user=user).exists()

        if profile_exists:
            # 이미 프로필 있으면 => 기존 유저 (로그인 상태)
            return Response({"message": "User already exists."}, status=status.HTTP_200_OK)
        # nickname = none 일경우
        if not nickname:
            nickname = generate_unique_username()
        # nickname이 중복인경우

        if Profile.objects.filter(nickname=nickname).exists():
            nickname = generate_unique_username()

        Profile.objects.create(user=user, nickname=nickname)
        Credits.objects.get_or_create(user=user)
        return Response({"message": "User profile created."}, status=status.HTTP_201_CREATED)



# 이메일 회원가입(profile)
class EmailSignupView(APIView):
    authentication_classes = [SupabaseJWTAuthentication]
    permission_classes = [AllowAny]

    def post(self, request):
        user = request.user
        nickname = getattr(user, "nickname", None)

        if not user or not user.email:
            return Response({"error": "Invalid user or email"}, status=status.HTTP_400_BAD_REQUEST)

        profile_exists = Profile.objects.filter(user=user).exists()

        if profile_exists:
            return Response({"message": "User already exists."}, status=status.HTTP_200_OK)

        # nickname = none 일경우
        if not nickname:
            nickname = generate_unique_username()
        # nickname이 중복인경우

        if Profile.objects.filter(nickname=nickname).exists():
            nickname = generate_unique_username()
        Profile.objects.create(user=user, nickname=nickname)
        Credits.objects.get_or_create(user=user)

        return Response({"nickname": nickname}, status=status.HTTP_201_CREATED)


# user 조회 / 수정 / 탈퇴
class UserViewSet(viewsets.ViewSet):
    authentication_classes = [SupabaseJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def retrieve(self, request):
        user = request.user
        serializer = UserSerializer(user,context={"request":request})
        return Response(serializer.data)

    def partial_update(self, request):
        user = request.user
        profile = getattr(user, "profile", None)
        if not profile:
            return Response({"detail": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)
        print("request.data",request.data)
        serializer = ProfileSerializer(
        profile,
        data=request.data,
        partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def destroy(self, request):
        user = request.user
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


