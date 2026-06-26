"""
sales/models.py

Core tables: Sale, SaleItem, Payment, CartSession.

Key rules:
- Sales are LOCKED immediately on save — no editing, no deletion ever.
- Every sale records the attendant, timestamp, and receipt number.
- Payment supports Cash, MoMo, Split (cash+MoMo), and Credit.
- Credit sales automatically link to a customer debt record.
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


# ─── Receipt Number Generator ─────────────────────────────────────────────────

def generate_receipt_number():
    """Sequential receipt number: RCP-YYYYMMDD-XXXX"""
    from django.db.models import Max
    today = timezone.now().date()
    prefix = f"RCP-{today:%Y%m%d}-"
    last = (
        Sale.objects
        .filter(receipt_number__startswith=prefix)
        .aggregate(Max('receipt_number'))['receipt_number__max']
    )
    if last:
        seq = int(last.split('-')[-1]) + 1
    else:
        seq = 1
    return f"{prefix}{seq:04d}"


# ─── Sale ─────────────────────────────────────────────────────────────────────

class Sale(models.Model):

    PAYMENT_METHOD_CHOICES = [
        ('cash',   'Cash'),
        ('momo',   'Mobile Money'),
        ('split',  'Split (Cash + MoMo)'),
        ('credit', 'Credit'),
    ]

    SALE_TYPE_CHOICES = [
        ('retail',    'Retail'),
        ('wholesale', 'Wholesale'),
    ]

    # Identity
    receipt_number = models.CharField(max_length=30, unique=True, editable=False)
    sale_type = models.CharField(max_length=10, choices=SALE_TYPE_CHOICES, default='retail')

    # Who and when
    attendant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='sales',
    )
    attendant_username = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    # Customer (optional for walk-in)
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='sales',
    )
    customer_name = models.CharField(
        max_length=200, blank=True,
        help_text="Copied at time of sale — survives customer deletion"
    )

    # Financials
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    installation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Payment
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    change_given = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Credit
    is_credit = models.BooleanField(default=False)
    credit_due_date = models.DateField(null=True, blank=True)

    # Discount
    discount = models.ForeignKey(
        'discounts.Discount',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='sales',
    )
    discount_code_used = models.CharField(max_length=50, blank=True)

    # Add-ons
    notes = models.TextField(blank=True)

    # LOCK — once saved, this sale cannot be modified or deleted
    locked = models.BooleanField(default=True, editable=False)

    class Meta:
        verbose_name = "Sale"
        verbose_name_plural = "Sales"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['attendant', '-created_at']),
            models.Index(fields=['customer', '-created_at']),
            models.Index(fields=['payment_method']),
        ]

    def __str__(self):
        return f"{self.receipt_number} — GH₵{self.total} ({self.created_at:%d %b %Y %H:%M})"

    # ── Computed properties ───────────────────────────────────────────────────

    @property
    def balance_due(self):
        return max(Decimal('0'), self.total - self.amount_paid)

    @property
    def is_fully_paid(self):
        return self.amount_paid >= self.total

    @property
    def item_count(self):
        return self.items.aggregate(
            total=models.Sum('quantity')
        )['total'] or 0

    @property
    def gross_profit(self):
        return sum(item.profit for item in self.items.all())

    @property
    def profit_margin(self):
        if self.total > 0:
            return (self.gross_profit / self.total) * 100
        return Decimal('0')

    # ── Save / Delete locking ─────────────────────────────────────────────────

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        if not is_new and self.locked:
            raise PermissionError(
                "Sales are locked and cannot be modified after creation."
            )

        if is_new:
            if not self.receipt_number:
                self.receipt_number = generate_receipt_number()
            self.locked = True
            if self.attendant and not self.attendant_username:
                self.attendant_username = self.attendant.username
            if self.customer and not self.customer_name:
                self.customer_name = str(self.customer)

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError(
            "Sales cannot be deleted. This is an anti-theft protection."
        )


# ─── SaleItem ─────────────────────────────────────────────────────────────────

class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.PROTECT, related_name='items')
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.PROTECT,
        related_name='sale_items',
    )
    product_unit = models.ForeignKey(
        'products.ProductUnit',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='sale_item',
        help_text="Specific serialised unit sold, if applicable",
    )

    # Snapshot prices at time of sale
    product_name = models.CharField(max_length=200)
    product_brand = models.CharField(max_length=100, blank=True)
    product_model = models.CharField(max_length=100, blank=True)
    serial_number = models.CharField(max_length=100, blank=True)

    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    cost_price = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Cost price at time of sale — for profit calculation"
    )
    item_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = "Sale Item"
        verbose_name_plural = "Sale Items"

    def __str__(self):
        return f"{self.product_name} x{self.quantity} @ GH₵{self.unit_price}"

    @property
    def profit(self):
        return self.subtotal - (self.cost_price * self.quantity)

    def save(self, *args, **kwargs):
        # Auto-calculate subtotal
        self.subtotal = (self.unit_price * self.quantity) - self.item_discount
        # Snapshot product details
        if not self.product_name:
            self.product_name = self.product.name
            self.product_brand = self.product.brand or ''
            self.product_model = self.product.model_number or ''
            self.cost_price = self.product.cost_price
        if self.product_unit and not self.serial_number:
            self.serial_number = self.product_unit.serial_number
        super().save(*args, **kwargs)


# ─── Payment ─────────────────────────────────────────────────────────────────

class Payment(models.Model):
    METHOD_CHOICES = [
        ('cash',   'Cash'),
        ('momo',   'Mobile Money'),
        ('credit', 'Credit'),
    ]

    sale = models.ForeignKey(Sale, on_delete=models.PROTECT, related_name='payments')
    method = models.CharField(max_length=10, choices=METHOD_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    momo_reference = models.CharField(
        max_length=100, blank=True,
        help_text="MoMo transaction ID or reference"
    )
    recorded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Payment"
        verbose_name_plural = "Payments"

    def __str__(self):
        return f"{self.get_method_display()} — GH₵{self.amount} ({self.sale.receipt_number})"


# ─── CartSession ──────────────────────────────────────────────────────────────

class CartSession(models.Model):
    """
    Temporary cart state while a sale is being built.
    Cleared once the sale is completed or abandoned.
    One active cart per attendant session.
    """
    session_key = models.CharField(max_length=64, unique=True)
    attendant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cart_sessions',
    )
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    sale_type = models.CharField(max_length=10, default='retail')

    # Cart items stored as JSON
    items_json = models.JSONField(default=list)

    # Applied discount
    discount = models.ForeignKey(
        'discounts.Discount',
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    discount_code = models.CharField(max_length=50, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Add-ons
    installation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cart Session"
        verbose_name_plural = "Cart Sessions"

    def __str__(self):
        return f"Cart — {self.attendant.username} ({self.item_count} items)"

    @property
    def item_count(self):
        return sum(item.get('quantity', 0) for item in self.items_json)

    @property
    def subtotal(self):
        return Decimal(str(sum(
            item.get('unit_price', 0) * item.get('quantity', 0)
            for item in self.items_json
        )))

    @property
    def total(self):
        return (
            self.subtotal
            - self.discount_amount
            + self.installation_fee
            + self.delivery_fee
        )

    def add_item(self, product, quantity=1, unit_price=None, product_unit=None):
        """Add or increment an item in the cart."""
        from products.models import Product
        price = unit_price or product.selling_price

        # Check if already in cart (match by product_id and unit_id)
        for item in self.items_json:
            if (item['product_id'] == product.pk and
                    item.get('product_unit_id') == (product_unit.pk if product_unit else None)):
                item['quantity'] += quantity
                item['subtotal'] = float(Decimal(str(item['unit_price'])) * item['quantity'])
                self.save()
                return

        entry = {
            'product_id': product.pk,
            'product_name': product.name,
            'product_brand': product.brand or '',
            'sku': product.sku or '',
            'product_unit_id': product_unit.pk if product_unit else None,
            'serial_number': product_unit.serial_number if product_unit else '',
            'quantity': quantity,
            'unit_price': float(price),
            'cost_price': float(product.cost_price),
            'subtotal': float(price * quantity),
        }
        self.items_json.append(entry)
        self.save()

    def remove_item(self, product_id, product_unit_id=None):
        self.items_json = [
            i for i in self.items_json
            if not (i['product_id'] == product_id and
                    i.get('product_unit_id') == product_unit_id)
        ]
        self.save()

    def update_quantity(self, product_id, quantity, product_unit_id=None):
        for item in self.items_json:
            if (item['product_id'] == product_id and
                    item.get('product_unit_id') == product_unit_id):
                if quantity <= 0:
                    self.remove_item(product_id, product_unit_id)
                    return
                item['quantity'] = quantity
                item['subtotal'] = item['unit_price'] * quantity
                self.save()
                return

    def clear(self):
        self.items_json = []
        self.discount = None
        self.discount_code = ''
        self.discount_amount = Decimal('0')
        self.installation_fee = Decimal('0')
        self.delivery_fee = Decimal('0')
        self.notes = ''
        self.customer = None
        self.save()