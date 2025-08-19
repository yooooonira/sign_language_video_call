from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin import site
from .views import jwt_admin_login

class PublicSchemaView(SpectacularAPIView):
    authentication_classes = []


class PublicSwaggerView(SpectacularSwaggerView):
    authentication_classes = []

urlpatterns = [
    path('admin/', admin.site.urls),
    path("admin/login/", jwt_admin_login, name="jwt_admin_login"),  # 커스텀 로그인 뷰 연결


    path("api/users/", include("user.urls")),
    path("api/credits/", include("credit.urls")),
    path("api/payments/", include("payment.urls")),
    path("api/notifications/", include("notification.urls")),
    path("api/calls/", include("call.urls")),
    path("api/friends/", include("friend.urls")),

    path('api-auth/', include('rest_framework.urls')),
    path('api/schema/', PublicSchemaView.as_view(), name='api-schema'),
    path('api/docs/', PublicSwaggerView.as_view(url_name='api-schema'), name='api-docs'),
]


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )