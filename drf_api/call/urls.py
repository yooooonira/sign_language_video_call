from django.urls import path,include
from . import views


urlpatterns = [

    path("", views.CallHistoryListView.as_view(),name="call-list"), #통화 기록 목록 조회 get 
    path("<int:pk>/", views.CallHistoryDetailView.as_view(), name="call-detail"), #특정 특정 기록 조회get
    path("record/", views.CallHistoryRecordView.as_view(), name="call-create"), #통화 정보 기록 post
]


