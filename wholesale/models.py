from django.db import models

# Create your models here.
from django.db import models
from django.conf import settings
from django.utils import timezone


class WholesaleOrder(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('packed', 'Packed'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('unpaid', 'Unpaid'),
        ('partial', 'Partially Paid'),
        ('paid', 'Fully Paid'),
    ]

    order_number = models.CharField(max_length=30, unique=True, editable=False)
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.PROTECT,
        related_name='wholesale_orders',
        limit_choices_to={'customer_type': 'wholesale'}
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='unpaid')

    order_date = models.DateField(default=timezone.now)
    delivery_date = models.DateField(null=True, blank=True)
    delivery_address = models.TextField(blank=True)

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    payment_method = models.CharField(max_length=30, choices=[
        ('cash', 'Cash'),
        ('momo', 'Mobile Money'),
        ('bank_transfer', 'Bank Transfer'),
        ('credit', 'Credit / On Account'),
        ('cheque', 'Cheque'),
    ], blank=True)
    payment_reference = models.CharField(max_length=100, blank=True)

    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='wholesale_orders_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.order_number} — {self.customer.name}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self._generate_order_number()
        self._recalculate_totals()
        self._update_payment_status()
        super().save(*args, **kwargs)

    def _generate_order_number(self):
        from datetime import date
        today = date.today()
        prefix = f"WS-{today.strftime('%Y%m%d')}-"
        last = WholesaleOrder.objects.filter(
            order_number__startswith=prefix
        ).order_by('-order_number').first()
        seq = 1
        if last:
            try:
                seq = int(last.order_number.split('-')[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        return f"{prefix}{seq:04d}"

    def _recalculate_totals(self):
        if self.pk:
            from django.db.models import Sum
            items_total = self.items.aggregate(
                total=Sum('line_total')
            )['total'] or 0
            self.subtotal = items_total
        self.grand_total = self.subtotal - self.discount_amount + self.delivery_fee

    def _update_payment_status(self):
        if self.amount_paid <= 0:
            self.payment_status = 'unpaid'
        elif self.amount_paid >= self.grand_total:
            self.payment_status = 'paid'
        else:
            self.payment_status = 'partial'

    @property
    def amount_due(self):
        return max(0, self.grand_total - self.amount_paid)

    @property
    def total_items(self):
        return self.items.count()

    def can_be_edited(self):
        return self.status in ('draft',)

    def confirm(self, user):
        if self.status != 'draft':
            raise ValueError("Only draft orders can be confirmed.")
        if not self.items.exists():
            raise ValueError("Cannot confirm an order with no items.")
        self.status = 'confirmed'
        self.save()

    def cancel(self):
        if self.status in ('delivered',):
            raise ValueError("Delivered orders cannot be cancelled.")
        self.status = 'cancelled'
        self.save()


class WholesaleOrderItem(models.Model):
    order = models.ForeignKey(
        WholesaleOrder,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.PROTECT
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ('order', 'product')

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"

    def save(self, *args, **kwargs):
        self.line_total = self.quantity * self.unit_price
        super().save(*args, **kwargs)
        # Sync order totals
        self.order._recalculate_totals()
        WholesaleOrder.objects.filter(pk=self.order_id).update(
            subtotal=self.order.subtotal,
            grand_total=self.order.grand_total,
        )

    @property
    def profit_margin(self):
        if self.unit_price and self.product.cost_price:
            return ((self.unit_price - self.product.cost_price) / self.unit_price) * 100
        return 0