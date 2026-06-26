from django.db import models
from django.conf import settings
from django.utils import timezone


class StockLevel(models.Model):
    """
    Tracks current quantity for each product.
    One record per product — updated every time stock moves.
    """
    product = models.OneToOneField(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='stock_level',
    )
    quantity = models.IntegerField(default=0)
    reserved_quantity = models.IntegerField(
        default=0,
        help_text="Units reserved for pending orders — not available for sale"
    )
    last_updated = models.DateTimeField(auto_now=True)
    last_updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='stock_updates',
    )

    class Meta:
        verbose_name = "Stock Level"
        verbose_name_plural = "Stock Levels"
        ordering = ['product__name']

    def __str__(self):
        return f"{self.product.name} — {self.quantity} units"

    @property
    def available_quantity(self):
        """Units available for sale (excludes reserved)."""
        return max(0, self.quantity - self.reserved_quantity)

    @property
    def is_low_stock(self):
        return self.quantity <= self.product.reorder_point

    @property
    def is_out_of_stock(self):
        return self.quantity <= 0

    @property
    def status(self):
        if self.is_out_of_stock:
            return 'out'
        if self.is_low_stock:
            return 'low'
        return 'ok'

    @property
    def status_label(self):
        return {
            'out': 'Out of Stock',
            'low': 'Low Stock',
            'ok': 'In Stock',
        }[self.status]

    @property
    def status_badge_class(self):
        return {
            'out': 'danger',
            'low': 'warning',
            'ok': 'success',
        }[self.status]

    def add_stock(self, qty, user=None):
        """Add units to stock. qty must be positive."""
        if qty <= 0:
            raise ValueError("Quantity to add must be positive.")
        self.quantity += qty
        self.last_updated_by = user
        self.save()

    def deduct_stock(self, qty, user=None):
        """Deduct units from stock. Raises if insufficient."""
        if qty <= 0:
            raise ValueError("Quantity to deduct must be positive.")
        if qty > self.quantity:
            raise ValueError(
                f"Insufficient stock. Available: {self.quantity}, Requested: {qty}"
            )
        self.quantity -= qty
        self.last_updated_by = user
        self.save()

    def set_quantity(self, qty, user=None):
        """Hard-set stock to a specific value (for manual count adjustments)."""
        if qty < 0:
            raise ValueError("Stock quantity cannot be negative.")
        self.quantity = qty
        self.last_updated_by = user
        self.save()


class StockMovement(models.Model):
    """
    Immutable log of every stock change.
    INSERT ONLY — records are never edited or deleted.
    """

    MOVEMENT_TYPES = [
        # Increases
        ('purchase',    'Purchase Received'),
        ('return',      'Customer Return'),
        ('adjustment_in', 'Manual Adjustment (In)'),
        ('initial',     'Initial Stock Entry'),
        # Decreases
        ('sale',        'Sale'),
        ('adjustment_out', 'Manual Adjustment (Out)'),
        ('damaged',     'Damaged / Written Off'),
        ('demo',        'Converted to Demo Unit'),
        # Neutral / informational
        ('demo_to_stock', 'Demo Unit Returned to Stock'),
        ('transfer',    'Stock Transfer'),
        ('count',       'Stock Count Correction'),
    ]

    INBOUND_TYPES = {'purchase', 'return', 'adjustment_in', 'initial', 'demo_to_stock', 'transfer'}
    OUTBOUND_TYPES = {'sale', 'adjustment_out', 'damaged', 'demo'}

    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='stock_movements',
    )
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    quantity = models.IntegerField(
        help_text="Always positive — direction is determined by movement_type"
    )
    quantity_before = models.IntegerField(
        help_text="Stock level before this movement"
    )
    quantity_after = models.IntegerField(
        help_text="Stock level after this movement"
    )

    # Reference linkage
    reference_type = models.CharField(
        max_length=30, blank=True,
        help_text="e.g. 'sale', 'purchase_order', 'return'"
    )
    reference_id = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="PK of the linked object (Sale, PurchaseOrder, Return, etc.)"
    )
    reference_label = models.CharField(
        max_length=100, blank=True,
        help_text="Human-readable reference saved at time of movement"
    )

    # Serial number if applicable
    serial_number = models.CharField(max_length=100, blank=True)

    note = models.TextField(blank=True, help_text="Reason or details for this movement")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='stock_movements_created',
    )
    created_by_username = models.CharField(
        max_length=150, blank=True,
        help_text="Username copied at time of movement — survives user deletion"
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Stock Movement"
        verbose_name_plural = "Stock Movements"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', '-created_at']),
            models.Index(fields=['movement_type', '-created_at']),
            models.Index(fields=['reference_type', 'reference_id']),
        ]

    def __str__(self):
        direction = "+" if self.movement_type in self.INBOUND_TYPES else "-"
        return (
            f"{self.product.name} | {direction}{self.quantity} | "
            f"{self.get_movement_type_display()} | {self.created_at:%d %b %Y %H:%M}"
        )

    @property
    def is_inbound(self):
        return self.movement_type in self.INBOUND_TYPES

    @property
    def is_outbound(self):
        return self.movement_type in self.OUTBOUND_TYPES

    @property
    def signed_quantity(self):
        """Quantity with direction sign (+/-)."""
        return self.quantity if self.is_inbound else -self.quantity

    @property
    def movement_icon(self):
        icons = {
            'purchase':       'fa-truck',
            'return':         'fa-undo',
            'adjustment_in':  'fa-plus-circle',
            'initial':        'fa-box',
            'sale':           'fa-shopping-cart',
            'adjustment_out': 'fa-minus-circle',
            'damaged':        'fa-exclamation-triangle',
            'demo':           'fa-eye',
            'demo_to_stock':  'fa-eye-slash',
            'transfer':       'fa-exchange-alt',
            'count':          'fa-clipboard-check',
        }
        return icons.get(self.movement_type, 'fa-circle')

    @property
    def movement_color(self):
        return 'success' if self.is_inbound else 'danger'

    def save(self, *args, **kwargs):
        # Copy username defensively — survives user deletion
        if self.created_by and not self.created_by_username:
            self.created_by_username = self.created_by.username
        # Prevent editing existing records
        if self.pk:
            raise PermissionError("Stock movements are immutable and cannot be edited.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("Stock movements cannot be deleted — audit trail is permanent.")


class DemoUnit(models.Model):
    """
    Tracks floor display / demo units separately from sellable stock.
    These cannot be sold without owner converting them back to sellable.
    """
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='demo_units',
    )
    serial_number = models.CharField(max_length=100, blank=True)
    condition_notes = models.TextField(
        blank=True,
        help_text="Description of demo unit condition"
    )
    converted_at = models.DateTimeField(default=timezone.now)
    converted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='demo_units_created',
    )
    is_active = models.BooleanField(
        default=True,
        help_text="False = returned to sellable stock"
    )
    returned_at = models.DateTimeField(null=True, blank=True)
    returned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='demo_units_returned',
    )

    class Meta:
        verbose_name = "Demo Unit"
        verbose_name_plural = "Demo Units"
        ordering = ['-converted_at']

    def __str__(self):
        status = "Active Demo" if self.is_active else "Returned to Stock"
        return f"{self.product.name} — {status} ({self.converted_at:%d %b %Y})"

    def return_to_stock(self, user):
        """Convert demo unit back to sellable stock."""
        self.is_active = False
        self.returned_at = timezone.now()
        self.returned_by = user
        self.save()


class StockAudit(models.Model):
    """
    Records physical stock count sessions.
    Owner can run a stock count, compare to system, and log discrepancies.
    """
    STATUS_CHOICES = [
        ('open',      'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    reference = models.CharField(
        max_length=20, unique=True,
        help_text="e.g. AUDIT-2025-001"
    )
    conducted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='stock_audits',
    )
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='open')
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Stock Audit"
        verbose_name_plural = "Stock Audits"
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.reference} — {self.get_status_display()} ({self.started_at:%d %b %Y})"

    @property
    def total_items(self):
        return self.items.count()

    @property
    def discrepancy_count(self):
        return self.items.filter(has_discrepancy=True).count()

    @property
    def total_discrepancy_value(self):
        from django.db.models import Sum, F, ExpressionWrapper, DecimalField
        result = self.items.filter(has_discrepancy=True).aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('discrepancy') * F('product__selling_price'),
                    output_field=DecimalField()
                )
            )
        )
        return result['total'] or 0


class StockAuditItem(models.Model):
    """One line in a stock audit — system count vs physical count."""
    audit = models.ForeignKey(StockAudit, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    system_count = models.IntegerField(help_text="What the system says")
    physical_count = models.IntegerField(help_text="What was actually counted")
    has_discrepancy = models.BooleanField(default=False)
    discrepancy = models.IntegerField(
        default=0,
        help_text="physical - system (negative = missing units)"
    )
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['audit', 'product']
        ordering = ['product__name']

    def __str__(self):
        return f"{self.product.name} | System: {self.system_count} | Physical: {self.physical_count}"

    def save(self, *args, **kwargs):
        self.discrepancy = self.physical_count - self.system_count
        self.has_discrepancy = self.discrepancy != 0
        super().save(*args, **kwargs)