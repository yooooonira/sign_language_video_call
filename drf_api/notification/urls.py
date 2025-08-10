from django.urls import path
from . import views


urlpatterns = [
    path("", views.NotificationListView.as_view()), #알림 목록 조회/삭제 (get, delete)
    path("<int:pk>", views.NotificationDetailView.as_view()),  #특정 알림 조회/삭제 (get, delete)
    path("<int:pk>/read", views.NotificationReadView.as_view()),  #특정 알림 읽음 처리  (patch)
    path("read-all", views.NotificationReadAllView.as_view()),  #전체 알림 읽음 처리  (patch)
]



