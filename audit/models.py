from django.db import models
from django.conf import settings


class AuditLog(models.Model):
    """
    Records every significant action taken in the POS system.
    Written by AuditMiddleware automatically + manually from views.
    """

    # ── Action categories ────────────────────────────────────────────────────
    CATEGORY_AUTH       = 'auth'
    CATEGORY_SALE       = 'sale'
    CATEGORY_PRODUCT    = 'product'
    CATEGORY_INVENTORY  = 'inventory'
    CATEGORY_PURCHASE   = 'purchase'
    CATEGORY_CUSTOMER   = 'customer'
    CATEGORY_EXPENSE    = 'expense'
    CATEGORY_RETURN     = 'return'
    CATEGORY_WHOLESALE  = 'wholesale'
    CATEGORY_DISCOUNT   = 'discount'
    CATEGORY_USER       = 'user'
    CATEGORY_REPORT     = 'report'
    CATEGORY_SYSTEM     = 'system'

    CATEGORY_CHOICES = [
        (CATEGORY_AUTH,      'Authentication'),
        (CATEGORY_SALE,      'Sale'),
        (CATEGORY_PRODUCT,   'Product'),
        (CATEGORY_INVENTORY, 'Inventory'),
        (CATEGORY_PURCHASE,  'Purchase'),
        (CATEGORY_CUSTOMER,  'Customer'),
        (CATEGORY_EXPENSE,   'Expense'),
        (CATEGORY_RETURN,    'Return'),
        (CATEGORY_WHOLESALE, 'Wholesale'),
        (CATEGORY_DISCOUNT,  'Discount'),
        (CATEGORY_USER,      'User Management'),
        (CATEGORY_REPORT,    'Report'),
        (CATEGORY_SYSTEM,    'System'),
    ]

    # ── Severity levels ──────────────────────────────────────────────────────
    LEVEL_INFO     = 'info'
    LEVEL_WARNING  = 'warning'
    LEVEL_CRITICAL = 'critical'

    LEVEL_CHOICES = [
        (LEVEL_INFO,     'Info'),
        (LEVEL_WARNING,  'Warning'),
        (LEVEL_CRITICAL, 'Critical'),
    ]

    # ── Fields ───────────────────────────────────────────────────────────────
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='audit_logs',
    )
    # Store username separately so logs survive user deletion
    username    = models.CharField(max_length=150, blank=True)
    user_role   = models.CharField(max_length=20, blank=True)   # owner / attendant

    category    = models.CharField(max_length=20, choices=CATEGORY_CHOICES, db_index=True)
    level       = models.CharField(max_length=10, choices=LEVEL_CHOICES, default=LEVEL_INFO)

    action      = models.CharField(max_length=255)          # Short verb: "Created sale #42"
    description = models.TextField(blank=True)              # Full detail if needed
    object_type = models.CharField(max_length=100, blank=True)  # e.g. 'Sale', 'Product'
    object_id   = models.CharField(max_length=50, blank=True)   # PK of the affected object
    object_repr = models.CharField(max_length=255, blank=True)  # Human string at time of action

    ip_address  = models.GenericIPAddressField(null=True, blank=True)
    timestamp   = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        indexes = [
            models.Index(fields=['category', 'timestamp']),
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['level', 'timestamp']),
        ]

    def __str__(self):
        who = self.username or 'System'
        return f"[{self.get_level_display()}] {who} — {self.action} ({self.timestamp:%Y-%m-%d %H:%M})"

    @property
    def level_badge_class(self):
        """Bootstrap badge colour for templates."""
        return {
            self.LEVEL_INFO:     'bg-info',
            self.LEVEL_WARNING:  'bg-warning text-dark',
            self.LEVEL_CRITICAL: 'bg-danger',
        }.get(self.level, 'bg-secondary')

    @property
    def category_icon(self):
        """Font-Awesome icon class per category."""
        return {
            self.CATEGORY_AUTH:      'fa-sign-in-alt',
            self.CATEGORY_SALE:      'fa-shopping-cart',
            self.CATEGORY_PRODUCT:   'fa-box',
            self.CATEGORY_INVENTORY: 'fa-warehouse',
            self.CATEGORY_PURCHASE:  'fa-truck',
            self.CATEGORY_CUSTOMER:  'fa-user',
            self.CATEGORY_EXPENSE:   'fa-receipt',
            self.CATEGORY_RETURN:    'fa-undo',
            self.CATEGORY_WHOLESALE: 'fa-store',
            self.CATEGORY_DISCOUNT:  'fa-tag',
            self.CATEGORY_USER:      'fa-users-cog',
            self.CATEGORY_REPORT:    'fa-chart-bar',
            self.CATEGORY_SYSTEM:    'fa-cog',
        }.get(self.category, 'fa-circle')