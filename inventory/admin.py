from django.contrib import admin
from django.utils.html import format_html
from .models import StockLevel, StockMovement, DemoUnit, StockAudit, StockAuditItem


@admin.register(StockLevel)
class StockLevelAdmin(admin.ModelAdmin):
    list_display = ['product', 'quantity', 'reserved_quantity', 'available_quantity',
                    'status_badge', 'last_updated']
    list_filter = ['last_updated']
    search_fields = ['product__name', 'product__brand', 'product__sku']
    readonly_fields = ['last_updated', 'available_quantity', 'is_low_stock']
    ordering = ['product__name']

    def status_badge(self, obj):
        colors = {'ok': 'green', 'low': 'orange', 'out': 'red'}
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors[obj.status],
            obj.status_label,
        )
    status_badge.short_description = 'Status'


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ['product', 'movement_type', 'signed_qty', 'quantity_before',
                    'quantity_after', 'created_by_username', 'created_at']
    list_filter = ['movement_type', 'created_at']
    search_fields = ['product__name', 'serial_number', 'note', 'created_by_username']
    readonly_fields = [f.name for f in StockMovement._meta.fields]  # All read-only
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    def has_add_permission(self, request):
        return False  # Created only through code

    def has_change_permission(self, request, obj=None):
        return False  # Immutable

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser  # Superuser only in extreme cases

    def signed_qty(self, obj):
        val = obj.signed_quantity
        color = 'green' if val > 0 else 'red'
        prefix = '+' if val > 0 else ''
        return format_html('<span style="color: {}; font-weight: bold;">{}{}</span>',
                           color, prefix, val)
    signed_qty.short_description = 'Qty Change'


@admin.register(DemoUnit)
class DemoUnitAdmin(admin.ModelAdmin):
    list_display = ['product', 'serial_number', 'is_active', 'converted_by', 'converted_at']
    list_filter = ['is_active', 'converted_at']
    search_fields = ['product__name', 'serial_number']
    readonly_fields = ['converted_at', 'returned_at']


class StockAuditItemInline(admin.TabularInline):
    model = StockAuditItem
    extra = 0
    readonly_fields = ['system_count', 'discrepancy', 'has_discrepancy']
    fields = ['product', 'system_count', 'physical_count', 'discrepancy', 'has_discrepancy', 'notes']


@admin.register(StockAudit)
class StockAuditAdmin(admin.ModelAdmin):
    list_display = ['reference', 'status', 'conducted_by', 'total_items',
                    'discrepancy_count', 'started_at', 'completed_at']
    list_filter = ['status', 'started_at']
    search_fields = ['reference', 'notes']
    readonly_fields = ['reference', 'started_at', 'completed_at', 'total_items', 'discrepancy_count']
    inlines = [StockAuditItemInline]