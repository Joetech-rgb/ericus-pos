from django.contrib import admin
from .models import Discount, DiscountUsage


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display  = (
        'name', 'code', 'discount_type', 'value', 'scope',
        'customer_target', 'times_used', 'is_active',
        'valid_from', 'valid_until',
    )
    list_filter   = ('discount_type', 'scope', 'customer_target', 'is_active', 'is_automatic', 'requires_pin')
    search_fields = ('name', 'code', 'description')
    readonly_fields = ('times_used', 'created_at', 'updated_at', 'created_by')
    filter_horizontal = ('products', 'categories')
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'code', 'description', 'is_active', 'is_automatic', 'requires_pin'),
        }),
        ('Discount Value', {
            'fields': ('discount_type', 'value', 'buy_quantity', 'get_quantity'),
        }),
        ('Scope & Target', {
            'fields': ('scope', 'customer_target', 'products', 'categories'),
        }),
        ('Conditions', {
            'fields': ('minimum_amount', 'maximum_discount'),
        }),
        ('Validity', {
            'fields': ('valid_from', 'valid_until', 'usage_limit', 'usage_limit_per_customer', 'times_used'),
        }),
        ('Meta', {
            'fields': ('created_by', 'created_at', 'updated_at'),
        }),
    )


@admin.register(DiscountUsage)
class DiscountUsageAdmin(admin.ModelAdmin):
    list_display  = ('discount', 'customer', 'sale', 'amount_saved', 'applied_by', 'applied_at')
    list_filter   = ('discount',)
    search_fields = ('discount__name', 'customer__full_name', 'customer__phone')
    readonly_fields = ('applied_at',)

    def has_add_permission(self, request):
        return False   # Usage records are created by the system only

    def has_change_permission(self, request, obj=None):
        return False