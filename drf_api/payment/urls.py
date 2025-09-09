from django.urls import path
from . import views


urlpatterns = [
    path("create/", views.PaymentPrepareView.as_view(), name="create-payment"),
    path("confirm/", views.ConfirmPaymentView.as_view(), name="confirm-payment"),
    path("webhook/", views.PaymentWebhookView.as_view(), name="payment-webhook"),  # 추가
]