from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.http import JsonResponse
from django.utils.timezone import now

class PublicSchemaView(SpectacularAPIView):
    authentication_classes = []


class PublicSwaggerView(SpectacularSwaggerView):
    authentication_classes = []

def health_check(request):
    return JsonResponse({"status": "ok", "time": now()})

urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/users/", include("user.urls")),
    path("api/credits/", include("credit.urls")),
    path("api/payments/", include("payment.urls")),
    path("api/notifications/", include("notification.urls")),
    path("api/calls/", include("call.urls")),
    path("api/friends/", include("friend.urls")),

    path('api-auth/', include('rest_framework.urls')),
    path('api/schema/', PublicSchemaView.as_view(), name='api-schema'),
    path('api/docs/', PublicSwaggerView.as_view(url_name='api-schema'), name='api-docs'),
    path('api/subscriptions/', include("subscription.urls")),
    path("", include("django_prometheus.urls")),
    path("health/", health_check, name="health_check"),
]




# 개발 모드(DEBUG=True)에서 Django가 직접 업로드된 미디어 파일을 서빙하게 함
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
