from core.utils import generate_order_id
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from .models import PaymentTransaction
import base64
import requests
from django.conf import settings
from credit.models import Credits
from django.utils import timezone


# 결제 주문 생성
class PaymentPrepareView(APIView):
    def post(self, request):
        try:
            price = int(request.data["price"])
        except (KeyError, ValueError):
            return Response({"detail": "Invalid credit_amount or price."}, status=400)

        payment = PaymentTransaction.objects.create(
            order_id=str(generate_order_id(request.user.id)),
            user=request.user,
            amount=price,
            status="READY",
        )
        return Response({"order_id": payment.order_id, "amount": payment.amount}, status=201)


class ConfirmPaymentView(APIView):

    def post(self, request):
        secret_key = settings.TOSS_SECRET_KEY

        data = request.data
        order_id = data.get("orderId")
        amount = data.get("amount")
        payment_key = data.get("paymentKey")

        if not order_id or not amount or not payment_key:
            return Response({"error": "Missing required parameters"}, status=status.HTTP_400_BAD_REQUEST)

        url = "https://api.tosspayments.com/v1/payments/confirm"
        headers = self.create_headers(secret_key)
        params = {
            "orderId": order_id,
            "amount": int(amount),
            "paymentKey": payment_key,
        }

        res_json, status_code = self.send_payment_request(url, params, headers)
        if status_code != 200:
            return Response({"error": "Payment confirmation failed", "detail": res_json},
                            status=status.HTTP_400_BAD_REQUEST)

        # 결제 성공 시 크레딧 충전
        user = request.user
        credit_to_add = int(amount) // 1000
        credit = Credits.objects.get(user=user)
        credit.remained_credit += credit_to_add
        credit.save()

        # 결제 트랜잭션 업데이트
        payment_transaction = PaymentTransaction.objects.get(order_id=order_id, user=user)
        payment_transaction.payment_key = payment_key
        payment_transaction.status = 'DONE'
        payment_transaction.amount = int(amount)
        payment_transaction.confirmed_at = timezone.now()
        payment_transaction.save()

        return Response(res_json)

    def create_headers(self, secret_key):
        userpass = f"{secret_key}:"
        encoded_u = base64.b64encode(userpass.encode()).decode()
        return {
            "Authorization": f"Basic {encoded_u}",
            "Content-Type": "application/json",
        }

    def send_payment_request(self, url, params, headers):
        response = requests.post(url, json=params, headers=headers)
        return response.json(), response.status_code
