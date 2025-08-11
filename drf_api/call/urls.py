from rest_framework.routers import DefaultRouter
from .views import CallHistoryViewSet

router = DefaultRouter()
router.register('calls', CallHistoryViewSet)

urlpatterns = router.urls

