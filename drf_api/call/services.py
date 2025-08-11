import math
from django.utils import timezone

CREDIT_PER_MINUTE = 1

def calc_used_credits(started_at, ended_at):
    if not (started_at and ended_at) or ended_at <= started_at:
        return 0
    seconds = (ended_at - started_at).total_seconds()
    minutes = math.ceil(seconds / 60.0)
    return int(minutes * CREDIT_PER_MINUTE)

def safe_end_time():
    return timezone.now()

def deduct_credits_for_call(call_obj):
    try:
        from credit.models import Credits
        credits = Credits.objects.select_for_update().get(user=call_obj.caller)
        credits.remained_credits = max(0, credits.remained_credits - call_obj.used_credits)
        credits.save(update_fields=['remained_credits'])
    except Exception:
        pass