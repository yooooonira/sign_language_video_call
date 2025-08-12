from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from .models import Credits
from .serializers import CreditsSerializer
from core.views import SupabaseJWTAuthentication
import requests


class CreditDetailView(APIView):
    authentication_classes = [SupabaseJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            credit = Credits.objects.get(user=request.user)
        except Credits.DoesNotExist:
            return Response({"detail": "Credit account not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = CreditsSerializer(credit)
        return Response(serializer.data, status=status.HTTP_200_OK)