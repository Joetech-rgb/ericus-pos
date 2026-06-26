from django.contrib import admin
from django.utils.html import format_html
from .models import Sale, SaleItem, Payment, CartSession


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = [f.name for f in SaleItem._meta.fields]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = [f.name for f in Payment._meta.fields]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = [
        'receipt_number', 'sale_type', 'attendant_username',
        'customer_name', 'payment_badge', 'total', 'created_at'
    ]
    list_filter = ['payment_method', 'sale_type', 'is_credit', 'created_at']
    search_fields = ['receipt_number', 'customer_name', 'attendant_username']
    readonly_fields = [f.name for f in Sale._meta.fields]
    date_hierarchy = 'created_at'
    inlines = [SaleItemInline, PaymentInline]
    ordering = ['-created_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False  # Sales are locked — no editing

    def has_delete_permission(self, request, obj=None):
        return False  # Sales cannot be deleted

    def payment_badge(self, obj):
        colors_map = {
            'cash': '#2ecc71', 'momo': '#3498db',
            'split': '#9b59b6', 'credit': '#e74c3c',
        }
        color = colors_map.get(obj.payment_method, '#95a5a6')
        return format_html(
            '<span style="background:{}; color:white; padding:2px 8px; '
            'border-radius:4px; font-size:11px;">{}</span>',
            color,
            obj.get_payment_method_display(),
        )
    payment_badge.short_description = 'Payment'


@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ['sale', 'product_name', 'quantity', 'unit_price', 'subtotal']
    search_fields = ['product_name', 'serial_number', 'sale__receipt_number']
    readonly_fields = [f.name for f in SaleItem._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['sale', 'method', 'amount', 'momo_reference', 'recorded_at']
    list_filter = ['method', 'recorded_at']
    readonly_fields = [f.name for f in Payment._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CartSession)
class CartSessionAdmin(admin.ModelAdmin):
    list_display = ['attendant', 'item_count', 'sale_type', 'updated_at']
    readonly_fields = ['session_key', 'created_at', 'updated_at', 'item_count', 'subtotal', 'total']
    list_filter = ['sale_type']

    def has_add_permission(self, request):
        return False