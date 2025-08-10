from rest_framework.permissions import BasePermission

class IsCallerOrReceiver(BasePermission):
    """
    통화 기록은 당사자만 열람/변경 가능
    """
    def has_object_permission(self, request, view, obj):
        uid = request.user.id
        return obj.caller_id == uid or obj.receiver_id == uid