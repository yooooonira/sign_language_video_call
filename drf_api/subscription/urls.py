from django.urls import path

from . import views

# api/friends
urlpatterns = [
    path("", views.SaveSubscriptionView.as_view()),
]
