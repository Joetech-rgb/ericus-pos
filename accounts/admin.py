from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, ShopProfile, OwnerPIN, FailedPINAttempt, UserSession


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display    = ['username', 'full_name', 'role', 'phone', 'is_active', 'date_joined']
    list_filter     = ['role', 'is_active']
    search_fields   = ['username', 'full_name', 'phone']
    ordering        = ['role', 'full_name']
    fieldsets       = (
        (None,           {'fields': ('username', 'password')}),
        ('Personal Info',{'fields': ('full_name', 'phone')}),
        ('Permissions',  {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'dark_mode')}),
        ('Dates',        {'fields': ('date_joined',)}),
    )
    add_fieldsets   = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'full_name', 'role', 'password1', 'password2'),
        }),
    )


@admin.register(ShopProfile)
class ShopProfileAdmin(admin.ModelAdmin):
    list_display  = ['name', 'phone', 'whatsapp', 'email']
    search_fields = ['name']


@admin.register(OwnerPIN)
class OwnerPINAdmin(admin.ModelAdmin):
    list_display  = ['user', 'attempts', 'locked_until', 'last_used']
    readonly_fields = ['pin_hash', 'attempts', 'locked_until', 'last_used']


@admin.register(FailedPINAttempt)
class FailedPINAttemptAdmin(admin.ModelAdmin):
    list_display  = ['user', 'action_attempted', 'timestamp', 'ip_address']
    list_filter   = ['action_attempted']
    readonly_fields = ['user', 'action_attempted', 'timestamp', 'ip_address']


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display  = ['user', 'last_activity', 'ip_address']
    readonly_fields = ['user', 'last_activity', 'session_key', 'ip_address', 'device']