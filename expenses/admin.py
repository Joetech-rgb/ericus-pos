from django.contrib import admin
from .models import Expense, ExpenseCategory


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display  = ('name', 'icon', 'is_active', 'created_at')
    list_filter   = ('is_active',)
    search_fields = ('name',)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display  = (
        'title', 'category', 'amount', 'payment_method',
        'expense_date', 'status', 'recorded_by', 'approved_by',
    )
    list_filter   = ('status', 'category', 'payment_method', 'is_recurring')
    search_fields = ('title', 'notes', 'reference')
    readonly_fields = ('created_at', 'updated_at', 'recorded_by', 'approved_by', 'approved_at')
    date_hierarchy = 'expense_date'
    ordering       = ('-expense_date',)
    fieldsets = (
        ('Expense Details', {
            'fields': ('category', 'title', 'amount', 'payment_method', 'reference',
                       'expense_date', 'notes', 'receipt_image'),
        }),
        ('Recurring', {
            'fields': ('is_recurring', 'recurrence_note'),
        }),
        ('Approval', {
            'fields': ('status', 'approved_by', 'approved_at', 'reject_reason'),
        }),
        ('Meta', {
            'fields': ('recorded_by', 'created_at', 'updated_at'),
        }),
    )