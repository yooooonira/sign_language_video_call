from django.contrib import admin
from .models import PaymentTransaction

@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'user', 'amount', 'status', 'requested_at', 'confirmed_at')
    list_filter = ('status', 'requested_at', 'confirmed_at')
    search_fields = ('order_id', 'user__email')
    readonly_fields = ('requested_at', 'confirmed_at')