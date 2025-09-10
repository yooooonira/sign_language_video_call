import base64
import json
import logging
from typing import List, Type

import requests  # type: ignore
from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils import generate_order_id
from credit.models import Credits

from .models import PaymentTransaction

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class PaymentWebhookView(View):
    authentication_classes: List[Type[BaseAuthentication]] = []
    permission_classes: List[Type[BasePermission]] = []

    def post(self, request):
        try:
            # JSON 데이터 파싱
            data = json.loads(request.body)

            # 로그 남기기
            logger.info(f"Toss Payments Webhook received: {data}")

            # 필수 필드 확인
            event_type = data.get("eventType")
            payment_data = data.get("data", {})

            if not event_type or not payment_data:
                logger.error("Invalid webhook data received")
                return HttpResponse("Invalid data", status=400)

            # 이벤트 타입에 따른 처리
            if event_type == "PAYMENT_STATUS_CHANGED":
                self._handle_payment_status_changed(payment_data)
            elif event_type == "PAYMENT_CANCELED":
                self._handle_cancel_status_changed(payment_data)
            elif event_type == "PAYMENT_FAILED":
                self._handle_payment_failed(payment_data)
            else:
                logger.info(f"Unhandled event type: {event_type}")

            return HttpResponse("OK", status=200)

        except json.JSONDecodeError:
            logger.error("Invalid JSON in webhook request")
            return HttpResponse("Invalid JSON", status=400)
        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
            return HttpResponse("Internal Server Error", status=500)

    def _handle_payment_status_changed(self, payment_data):
        """결제 상태 변경 처리"""
        order_id = payment_data.get("orderId")
        status_value = payment_data.get("status")
        payment_key = payment_data.get("paymentKey")
        amount = payment_data.get("totalAmount", 0)

        if not order_id:
            logger.error("No orderId in payment data")
            return

        try:
            with transaction.atomic():
                payment_transaction = (
                    PaymentTransaction.objects.select_for_update().get(
                        order_id=order_id
                    )
                )

                # 상태가 이미 처리되었다면 중복 처리 방지
                if payment_transaction.status == "DONE" and status_value == "DONE":
                    logger.info(f"Payment {order_id} already processed")
                    return

                if status_value == "DONE":
                    # 결제 완료 처리
                    payment_transaction.status = "DONE"
                    payment_transaction.payment_key = payment_key
                    payment_transaction.amount = amount
                    payment_transaction.confirmed_at = timezone.now()
                    payment_transaction.save()

                    # 크레딧 충전
                    credit_to_add = amount // 1000
                    credit = Credits.objects.select_for_update().get(
                        user=payment_transaction.user
                    )
                    credit.remained_credit += credit_to_add
                    credit.last_updated = timezone.now()
                    credit.save()

                    logger.info(
                        f"Payment {order_id} completed. Added {credit_to_add} credits"
                    )

                elif status_value in ["CANCELED", "PARTIAL_CANCELED"]:
                    # 결제 취소 처리
                    payment_transaction.status = "CANCELED"
                    payment_transaction.save()

                    logger.info(f"Payment {order_id} canceled")

        except PaymentTransaction.DoesNotExist:
            logger.error(f"PaymentTransaction not found for orderId: {order_id}")
        except Credits.DoesNotExist:
            logger.error(f"Credits not found for user: {payment_transaction.user}")
        except Exception as e:
            logger.error(f"Error handling payment status change: {str(e)}")

    def _handle_cancel_status_changed(self, payment_data):
        """결제 취소 처리"""
        order_id = payment_data.get("orderId")

        if not order_id:
            return

        try:
            payment_transaction = PaymentTransaction.objects.get(order_id=order_id)
            payment_transaction.status = "CANCELED"
            payment_transaction.save()

            logger.info(f"Payment {order_id} marked as canceled")

        except PaymentTransaction.DoesNotExist:
            logger.error(f"PaymentTransaction not found for orderId: {order_id}")


# 결제 주문 생성
class PaymentPrepareView(APIView):
    def post(self, request):
        try:
            price = int(request.data["price"])
        except (KeyError, ValueError):
            return Response({"detail": "Invalid credit_amount or price."}, status=400)

        payment = PaymentTransaction.objects.create(
            order_id=str(generate_order_id.generate_order_id(str(request.user.id))),
            user=request.user,
            amount=price,
            status="READY",
        )
        return Response(
            {"order_id": payment.order_id, "amount": payment.amount}, status=201
        )


class ConfirmPaymentView(APIView):
    def post(self, request):
        secret_key = settings.TOSS_SECRET_KEY

        data = request.data
        order_id = data.get("orderId")
        amount = data.get("amount")
        payment_key = data.get("paymentKey")

        if not order_id or not amount or not payment_key:
            return Response(
                {"error": "Missing required parameters"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 결제 확인 요청
        url = "https://api.tosspayments.com/v1/payments/confirm"
        headers = self.create_headers(secret_key)
        params = {
            "orderId": order_id,
            "amount": int(amount),
            "paymentKey": payment_key,
        }

        res_json, status_code = self.send_payment_request(url, params, headers)

        if status_code != 200:
            # 실패 시 결제 상태 업데이트
            try:
                payment_transaction = PaymentTransaction.objects.get(
                    order_id=order_id, user=request.user
                )
                payment_transaction.status = "FAILED"
                payment_transaction.save()
            except PaymentTransaction.DoesNotExist:
                pass

            return Response(
                {"error": "Payment confirmation failed", "detail": res_json},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 성공 시 webhook에서 최종 처리되므로 여기서는 응답만 반환
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
