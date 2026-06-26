from django.contrib import admin
from django.utils.html import format_html
from .models import WholesaleOrder, WholesaleOrderItem


class WholesaleOrderItemInline(admin.TabularInline):
    model = WholesaleOrderItem
    extra = 0
    readonly_fields = ('line_total',)
    fields = ('product', 'quantity', 'unit_price', 'line_total', 'notes')


@admin.register(WholesaleOrder)
class WholesaleOrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_number', 'customer', 'status', 'payment_status_badge',
        'grand_total_display', 'amount_paid', 'amount_due_display',
        'order_date', 'created_by',
    )
    list_filter = ('status', 'payment_status', 'payment_method', 'order_date')
    search_fields = ('order_number', 'customer__name', 'payment_reference')
    readonly_fields = (
        'order_number', 'subtotal', 'grand_total', 'payment_status',
        'amount_due', 'created_by', 'created_at', 'updated_at',
    )
    inlines = [WholesaleOrderItemInline]
    date_hierarchy = 'order_date'
    ordering = ('-created_at',)

    fieldsets = (
        ('Order Info', {
            'fields': (
                'order_number', 'customer', 'status',
                'order_date', 'delivery_date', 'delivery_address',
            )
        }),
        ('Financials', {
            'fields': (
                'subtotal', 'discount_amount', 'delivery_fee', 'grand_total',
            )
        }),
        ('Payment', {
            'fields': (
                'payment_status', 'amount_paid', 'amount_due',
                'payment_method', 'payment_reference',
            )
        }),
        ('Meta', {
            'fields': ('notes', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    @admin.display(description='Payment')
    def payment_status_badge(self, obj):
        colours = {
            'unpaid': '#dc3545',
            'partial': '#fd7e14',
            'paid': '#198754',
        }
        colour = colours.get(obj.payment_status, '#6c757d')
        return format_html(
            '<span style="color:white;background:{};padding:2px 8px;border-radius:4px;font-size:11px;">{}</span>',
            colour,
            obj.get_payment_status_display(),
        )

    @admin.display(description='Grand Total', ordering='grand_total')
    def grand_total_display(self, obj):
        return f"GH₵{obj.grand_total:,.2f}"

    @admin.display(description='Amount Due')
    def amount_due_display(self, obj):
        due = obj.amount_due
        colour = '#dc3545' if due > 0 else '#198754'
        return format_html('<span style="color:{};">GH₵{:,.2f}</span>', colour, due)


@admin.register(WholesaleOrderItem)
class WholesaleOrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'unit_price', 'line_total')
    list_filter = ('order__status',)
    search_fields = ('order__order_number', 'product__name')
    readonly_fields = ('line_total',)