from django.http import JsonResponse

# Create your views here.
def test_view(request):
    return JsonResponse({"message": "Hello from test_view!"})