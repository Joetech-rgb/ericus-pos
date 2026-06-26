from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display  = ('timestamp', 'username', 'user_role', 'level', 'category', 'action', 'ip_address')
    list_filter   = ('level', 'category', 'user_role')
    search_fields = ('username', 'action', 'description', 'object_repr', 'ip_address')
    readonly_fields = [f.name for f in AuditLog._meta.get_fields()]  # All fields read-only
    date_hierarchy = 'timestamp'
    ordering       = ('-timestamp',)

    def has_add_permission(self, request):
        return False   # Logs are created by the system, not manually

    def has_change_permission(self, request, obj=None):
        return False   # Audit logs must never be edited

    def has_delete_permission(self, request, obj=None):
        # Only superusers can delete individual log entries from admin
        return request.user.is_superuser