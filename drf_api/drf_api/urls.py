from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.views.decorators.csrf import csrf_exempt
class PublicSchemaView(SpectacularAPIView):
    authentication_classes = []


class PublicSwaggerView(SpectacularSwaggerView):
    authentication_classes = []

urlpatterns = [
    path('admin/', admin.site.urls),
    path("admin/login/", csrf_exempt(site.login)),

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