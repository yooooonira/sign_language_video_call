from django.contrib import admin
from .models import Credits


@admin.register(Credits)
class CreditAdmin(admin.ModelAdmin):
    list_display = ('user', 'remained_credit', 'last_updated', 'last_used')
    search_fields = ('user__email',)
    readonly_fields = ('last_updated', 'last_used')

    def has_add_permission(self, request):
        # Credit 객체는 유저 생성 시 자동 생성되므로 admin에서 수동 추가 못 하게 함
        return False
