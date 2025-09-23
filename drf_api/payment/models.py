from django.conf import settings
from django.db import models


class PaymentTransaction(models.Model):
    STATUS_CHOICES = [
        ("READY", "결제 요청됨"),
        ("DONE", "결제 완료"),
        ("FAILED", "결제 실패"),
        ("CANCELED", "결제 취소"),
    ]
    payment_key: models.CharField = models.CharField(
        max_length=100, unique=True, null=True, blank=True
    )
    order_id: models.CharField = models.CharField(
        max_length=100, unique=True
    )  # 유저 주문번호
    user: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE
    )

    amount: models.PositiveIntegerField = models.PositiveIntegerField()  # 결제 금액
    status: models.CharField = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="READY"
    )

    requested_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    confirmed_at: models.DateTimeField = models.DateTimeField(
        null=True, blank=True
    )  # 결제 완료 시간

    class Meta:
        ordering = ["-requested_at"]
        verbose_name = "Payment Transaction"
        verbose_name_plural = "Payment Transactions"

    def __str__(self) -> str:
        return f"[{self.user.email}] {self.amount}원 - {self.status}"
