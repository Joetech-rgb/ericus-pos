from django.db import models
from django.conf import settings


class SavedReport(models.Model):
    """Stores generated report metadata so owner can re-run them."""

    REPORT_TYPE_CHOICES = [
        ('sales_summary', 'Sales Summary'),
        ('sales_by_product', 'Sales by Product'),
        ('sales_by_attendant', 'Sales by Attendant'),
        ('sales_by_customer', 'Sales by Customer'),
        ('inventory_status', 'Inventory Status'),
        ('low_stock', 'Low Stock Report'),
        ('expense_summary', 'Expense Summary'),
        ('expense_by_category', 'Expenses by Category'),
        ('profit_loss', 'Profit & Loss'),
        ('purchase_summary', 'Purchase Summary'),
        ('customer_credit', 'Customer Credit Report'),
        ('returns_summary', 'Returns Summary'),
        ('discount_usage', 'Discount Usage'),
        ('wholesale_summary', 'Wholesale Summary'),
        ('attendant_performance', 'Attendant Performance'),
    ]

    FORMAT_CHOICES = [
        ('screen', 'On Screen'),
        ('pdf', 'PDF Download'),
        ('csv', 'CSV Download'),
    ]

    name = models.CharField(max_length=200)
    report_type = models.CharField(max_length=50, choices=REPORT_TYPE_CHOICES)
    format = models.CharField(max_length=10, choices=FORMAT_CHOICES, default='screen')
    parameters = models.JSONField(default=dict, blank=True)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='saved_reports'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_report_type_display()})"