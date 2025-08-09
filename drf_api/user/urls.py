from django.urls import path
from . import views

user_view = views.UserViewSet.as_view({
    'get': 'retrieve',
    'patch': 'partial_update',
    'delete': 'destroy',
})

urlpatterns = [
    path("signup/", views.SocialSignupView.as_view(), name='email-signup'),
    path("social-signup/", views.EmailSignupView.as_view(), name='social-signup'),
    path('me/', user_view, name='user-me'),

]

