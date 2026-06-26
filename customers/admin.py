from django.contrib import admin
from .models import Customer, CreditPayment


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display  = (
        'full_name', 'phone', 'customer_type', 'credit_balance',
        'loyalty_points', 'is_active', 'created_at',
    )
    list_filter   = ('customer_type', 'is_active')
    search_fields = ('full_name', 'phone', 'company_name', 'email')
    readonly_fields = ('created_at', 'updated_at', 'created_by')
    fieldsets = (
        ('Basic Info', {
            'fields': ('full_name', 'phone', 'phone_alt', 'email', 'company_name', 'address', 'customer_type'),
        }),
        ('Credit & Loyalty', {
            'fields': ('credit_limit', 'credit_balance', 'loyalty_points'),
        }),
        ('Status', {
            'fields': ('is_active', 'notes', 'created_by', 'created_at', 'updated_at'),
        }),
    )


@admin.register(CreditPayment)
class CreditPaymentAdmin(admin.ModelAdmin):
    list_display  = ('customer', 'amount', 'payment_method', 'reference', 'recorded_by', 'created_at')
    list_filter   = ('payment_method',)
    search_fields = ('customer__full_name', 'customer__phone', 'reference')
    readonly_fields = ('created_at', 'recorded_by')