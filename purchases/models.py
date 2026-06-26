from django.db import models
from django.conf import settings
from django.utils import timezone
#from django.core.exceptions import PermissionError
import uuid


class Supplier(models.Model):
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    alternate_phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def total_orders(self):
        return self.purchaseorder_set.count()

    @property
    def total_spent(self):
        from django.db.models import Sum
        result = self.purchaseorder_set.filter(
            status='received'
        ).aggregate(total=Sum('grand_total'))
        return result['total'] or 0

    @property
    def pending_orders(self):
        return self.purchaseorder_set.filter(
            status__in=['draft', 'ordered', 'partial']
        ).count()


class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('ordered', 'Ordered'),
        ('partial', 'Partially Received'),
        ('received', 'Fully Received'),
        ('cancelled', 'Cancelled'),
    ]

    po_number = models.CharField(max_length=30, unique=True, editable=False)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    order_date = models.DateField(default=timezone.now)
    expected_date = models.DateField(null=True, blank=True)
    received_date = models.DateField(null=True, blank=True)

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=30, choices=[
        ('cash', 'Cash'),
        ('momo', 'Mobile Money'),
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('credit', 'Credit / On Account'),
    ], blank=True)
    payment_reference = models.CharField(max_length=100, blank=True)

    notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='purchase_orders_created'
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='purchase_orders_approved'
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.po_number} — {self.supplier.name}"

    def save(self, *args, **kwargs):
        if not self.po_number:
            self.po_number = self._generate_po_number()
        self._recalculate_totals()
        super().save(*args, **kwargs)

    def _generate_po_number(self):
        from datetime import date
        today = date.today()
        prefix = f"PO-{today.strftime('%Y%m%d')}-"
        last = PurchaseOrder.objects.filter(
            po_number__startswith=prefix
        ).order_by('-po_number').first()
        if last:
            try:
                seq = int(last.po_number.split('-')[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f"{prefix}{seq:04d}"

    def _recalculate_totals(self):
        if self.pk:
            from django.db.models import Sum
            items_total = self.items.aggregate(
                total=Sum('line_total')
            )['total'] or 0
            self.subtotal = items_total
        self.grand_total = (
            self.subtotal
            - self.discount_amount
            + self.tax_amount
            + self.shipping_cost
        )

    @property
    def amount_due(self):
        return self.grand_total - self.amount_paid

    @property
    def is_fully_paid(self):
        return self.amount_paid >= self.grand_total

    @property
    def total_items(self):
        return self.items.count()

    @property
    def total_units_ordered(self):
        from django.db.models import Sum
        return self.items.aggregate(
            total=Sum('quantity_ordered')
        )['total'] or 0

    @property
    def total_units_received(self):
        from django.db.models import Sum
        return self.items.aggregate(
            total=Sum('quantity_received')
        )['total'] or 0

    def can_be_edited(self):
        return self.status in ('draft',)

    def can_be_cancelled(self):
        return self.status in ('draft', 'ordered')

    def mark_ordered(self, user):
        if self.status != 'draft':
            raise ValueError("Only draft orders can be marked as ordered.")
        if not self.items.exists():
            raise ValueError("Cannot order a PO with no items.")
        self.status = 'ordered'
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save()

    def cancel(self, user):
        if not self.can_be_cancelled():
            raise ValueError("This order cannot be cancelled.")
        self.status = 'cancelled'
        self.save()

    def update_status_from_items(self):
        """Called after a GRN to sync PO status."""
        total_ordered = self.total_units_ordered
        total_received = self.total_units_received
        if total_received == 0:
            pass  # stays as 'ordered'
        elif total_received >= total_ordered:
            self.status = 'received'
            self.received_date = timezone.now().date()
        else:
            self.status = 'partial'
        self.save()


class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.PROTECT
    )
    quantity_ordered = models.PositiveIntegerField(default=1)
    quantity_received = models.PositiveIntegerField(default=0)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ('purchase_order', 'product')

    def __str__(self):
        return f"{self.product.name} x{self.quantity_ordered}"

    def save(self, *args, **kwargs):
        self.line_total = self.quantity_ordered * self.unit_cost
        super().save(*args, **kwargs)
        # Recalculate PO totals whenever an item changes
        self.purchase_order._recalculate_totals()
        PurchaseOrder.objects.filter(pk=self.purchase_order_id).update(
            subtotal=self.purchase_order.subtotal,
            grand_total=self.purchase_order.grand_total,
        )

    @property
    def quantity_pending(self):
        return max(0, self.quantity_ordered - self.quantity_received)

    @property
    def is_fully_received(self):
        return self.quantity_received >= self.quantity_ordered


class GoodsReceivedNote(models.Model):
    """Records each delivery/receiving event against a PO."""
    grn_number = models.CharField(max_length=30, unique=True, editable=False)
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.PROTECT,
        related_name='grns'
    )
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='grns_received'
    )
    received_date = models.DateField(default=timezone.now)
    delivery_note_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-received_date', '-created_at']
        verbose_name = 'Goods Received Note'
        verbose_name_plural = 'Goods Received Notes'

    def __str__(self):
        return f"{self.grn_number} — {self.purchase_order.po_number}"

    def save(self, *args, **kwargs):
        if not self.grn_number:
            self.grn_number = self._generate_grn_number()
        super().save(*args, **kwargs)

    def _generate_grn_number(self):
        from datetime import date
        today = date.today()
        prefix = f"GRN-{today.strftime('%Y%m%d')}-"
        last = GoodsReceivedNote.objects.filter(
            grn_number__startswith=prefix
        ).order_by('-grn_number').first()
        if last:
            try:
                seq = int(last.grn_number.split('-')[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f"{prefix}{seq:04d}"

    @property
    def total_units_received(self):
        from django.db.models import Sum
        return self.grn_items.aggregate(
            total=Sum('quantity_received')
        )['total'] or 0


class GRNItem(models.Model):
    grn = models.ForeignKey(
        GoodsReceivedNote,
        on_delete=models.CASCADE,
        related_name='grn_items'
    )
    po_item = models.ForeignKey(
        PurchaseOrderItem,
        on_delete=models.PROTECT,
        related_name='grn_items'
    )
    quantity_received = models.PositiveIntegerField(default=0)
    condition = models.CharField(max_length=20, choices=[
        ('new', 'New'),
        ('damaged', 'Damaged'),
    ], default='new')
    notes = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"{self.po_item.product.name} x{self.quantity_received}"