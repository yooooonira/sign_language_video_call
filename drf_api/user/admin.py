from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, Profile
from django.contrib import admin


class UserAdmin(BaseUserAdmin):
    """Define the admin pages for users"""
    ordering = ['id']
    list_display = ['email']
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (
            _('Permissions'),
            {
                'fields': (
                  'is_active',
                  'is_staff',
                  'is_superuser',
                )
            }
        ),
        (_('Important dates'), {'fields': ('last_login',)}),
    )
    readonly_fields = ['last_login']
    add_fieldsets = (
      (None, {
          'classes': ('wide',),
          'fields': (
              'email',
              'password1',
              'password2',
              'is_active',
              'is_staff',
              'is_superuser',
          ),
      }),
    )


admin.site.register(User, UserAdmin)
admin.site.register(Profile)
