from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Credits
from .serializers import CreditsSerializer


class CreditDetailView(APIView):
    def get(self, request):
        try:
            credit = Credits.objects.get(user=request.user)
        except Credits.DoesNotExist:
            return Response({"detail": "Credit account not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = CreditsSerializer(credit)
        return Response(serializer.data, status=status.HTTP_200_OK)
