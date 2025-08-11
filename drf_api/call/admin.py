from django.contrib import admin
from .models import CallHistory

@admin.register(CallHistory)
class CallHistoryAdmin(admin.ModelAdmin):
    list_display = (
        'id','caller','receiver','call_status',
        'started_at','ended_at','used_credits','called_at'
    )
    list_filter = ('call_status','called_at')
    search_fields = ('caller__email','receiver__email')
