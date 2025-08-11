from django.urls import path
from . import views


urlpatterns = [
    # API Views
    path("api/credits/", views.CreditDetailView.as_view(), name="credits_detail"),
]