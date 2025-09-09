from django.urls import path

from . import views

urlpatterns = [
    path("", views.CallHistoryListView.as_view(), name="call-list"),  # 통화 기록 목록 조회 get
    path("<int:pk>/", views.CallHistoryDetailView.as_view(), name="call-detail"),  # 특정 특정 기록 조회get/delete
    path("record/", views.CallHistoryRecordView.as_view(), name="call-create"),  # 통화 정보 기록 post

    path("start/", views.CallRequestView.as_view(), name="call-start"),  # 통화 요청 POST
    path("accept/", views.CallAcceptView.as_view(), name="call-accept"),  # 통화 수락 POST
    path("reject/", views.CallRejectView.as_view(), name="call-reject"),  # 통화 거절 POST
    path("missed/", views.CallMissedView.as_view(), name="call-missed"),  # 부재중 POST
    path("end/", views.CallEndView.as_view(), name="call-end"),  # 통화 종료 POST
]
