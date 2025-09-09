from django.urls import path

from . import views

urlpatterns = [
    # API Views
    path("", views.CreditDetailView.as_view(), name="credits_detail"),
]
