from django.contrib import admin
from .models import Return


@admin.register(Return)
class ReturnAdmin(admin.ModelAdmin):
    list_display = [
        'return_number', 'product', 'customer', 'reason',
        'status', 'resolution', 'refund_amount', 'return_date', 'processed_by'
    ]
    list_filter = ['status', 'reason', 'resolution', 'condition', 'return_date']
    search_fields = ['return_number', 'product__name', 'customer__name', 'serial_number']
    readonly_fields = [
        'return_number', 'processed_by', 'approved_by',
        'approved_at', 'created_at', 'updated_at'
    ]
    date_hierarchy = 'return_date'

    fieldsets = (
        ('Return Info', {
            'fields': ('return_number', 'sale', 'sale_item', 'customer', 'product', 'quantity', 'serial_number', 'return_date')
        }),
        ('Reason', {
            'fields': ('reason', 'reason_detail', 'condition')
        }),
        ('Resolution', {
            'fields': ('status', 'resolution', 'resolution_notes', 'refund_amount', 'restocking_fee', 'return_to_stock', 'mark_as_damaged')
        }),
        ('People & Timestamps', {
            'fields': ('processed_by', 'approved_by', 'approved_at', 'created_at', 'updated_at')
        }),
    )