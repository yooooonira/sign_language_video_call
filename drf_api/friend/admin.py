from django.contrib import admin

from .models import Friend, FriendRelations


@admin.register(FriendRelations)
class FriendRelationsAdmin(admin.ModelAdmin):
    list_display = ("from_user", "to_user", "status")
    list_filter = ("status",)
    search_fields = ("from_user__email", "to_user__email")


@admin.register(Friend)
class FriendAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at")
    filter_horizontal = ("users",)  # add할때 편함
