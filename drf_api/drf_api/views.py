# core/views.py
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse

@csrf_exempt
def jwt_admin_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_staff:
            login(request, user)
            return HttpResponseRedirect(reverse("admin:index"))
    # GET 또는 실패 시 로그인 폼 보여주기
    return HttpResponse("Custom Admin Login Page (CSRF Exempt)")
