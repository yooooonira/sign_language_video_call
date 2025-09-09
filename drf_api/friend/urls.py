from django.urls import path

from . import views

# api/friends
urlpatterns = [

    path("", views.FriendListView.as_view()),  # 친구 목록 조회 get
    path("<int:pk>/", views.FriendRetrieveDeleteView.as_view()),  # 친구 프로필 조회, 친구 삭제 get/delete
    path("requests/received/", views.ReceivedRequestListView.as_view()),  # 친추 받은 목록 조회 get
    path("requests/sent/", views.SentRequestListView.as_view()),  # 친추 보낸 목록 조회 get

    path("requests/", views.FriendRequestCreateView.as_view()),   # 친구 추가 post
    path("requests/<int:pk>/accept/", views.FriendRequestAcceptView.as_view()),   # 친구 수락 post
    path("requests/<int:pk>/reject/", views.FriendRequestRejectView.as_view()),   # 친구 거절 post
    path("requests/<int:pk>/", views.FriendRequestDestroyView.as_view()),  # 친구 요청 취소 delete
]
