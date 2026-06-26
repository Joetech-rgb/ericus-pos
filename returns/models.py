from django.db import models
from django.conf import settings
from django.utils import timezone


class Return(models.Model):
    REASON_CHOICES = [
        ('defective', 'Defective / Not Working'),
        ('wrong_item', 'Wrong Item Delivered'),
        ('customer_change_mind', 'Customer Changed Mind'),
        ('damaged_in_transit', 'Damaged in Transit'),
        ('warranty_claim', 'Warranty Claim'),
        ('overcharged', 'Overcharged / Billing Error'),
        ('other', 'Other'),
    ]

    RESOLUTION_CHOICES = [
        ('refund_cash', 'Cash Refund'),
        ('refund_momo', 'MoMo Refund'),
        ('exchange', 'Exchange for Same Item'),
        ('exchange_different', 'Exchange for Different Item'),
        ('store_credit', 'Store Credit / Credit Note'),
        ('repair', 'Sent for Repair'),
        ('rejected', 'Return Rejected'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('resolved', 'Resolved'),
        ('rejected', 'Rejected'),
    ]

    # Auto-generated return number
    return_number = models.CharField(max_length=30, unique=True, editable=False)

    # Links
    sale = models.ForeignKey(
        'sales.Sale',
        on_delete=models.PROTECT,
        related_name='returns'
    )
    sale_item = models.ForeignKey(
        'sales.SaleItem',
        on_delete=models.PROTECT,
        related_name='returns',
        null=True, blank=True,
        help_text="The specific item being returned. Leave blank if whole sale."
    )
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='returns'
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.PROTECT,
        related_name='returns'
    )

    # Return details
    quantity = models.PositiveIntegerField(default=1)
    serial_number = models.CharField(max_length=100, blank=True)
    reason = models.CharField(max_length=30, choices=REASON_CHOICES)
    reason_detail = models.TextField(blank=True, help_text="Additional details about the reason")
    condition = models.CharField(max_length=20, choices=[
        ('working', 'Still Working'),
        ('faulty', 'Faulty / Not Working'),
        ('damaged', 'Physically Damaged'),
        ('missing_parts', 'Missing Parts/Accessories'),
    ], default='faulty')

    # Resolution
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    resolution = models.CharField(max_length=30, choices=RESOLUTION_CHOICES, blank=True)
    resolution_notes = models.TextField(blank=True)

    # Financials
    original_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    restocking_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Stock action
    return_to_stock = models.BooleanField(
        default=False,
        help_text="Add the returned unit back to sellable stock"
    )
    mark_as_damaged = models.BooleanField(
        default=False,
        help_text="Log as damaged stock (not sellable)"
    )

    # People
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='returns_processed'
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='returns_approved'
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    return_date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.return_number} — {self.product.name}"

    def save(self, *args, **kwargs):
        if not self.return_number:
            self.return_number = self._generate_return_number()
        super().save(*args, **kwargs)

    def _generate_return_number(self):
        from datetime import date
        today = date.today()
        prefix = f"RTN-{today.strftime('%Y%m%d')}-"
        last = Return.objects.filter(
            return_number__startswith=prefix
        ).order_by('-return_number').first()
        if last:
            try:
                seq = int(last.return_number.split('-')[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f"{prefix}{seq:04d}"

    @property
    def net_refund(self):
        return max(0, self.refund_amount - self.restocking_fee)

    @property
    def is_pending(self):
        return self.status == 'pending'

    @property
    def is_resolved(self):
        return self.status == 'resolved'

    def approve(self, user):
        self.status = 'approved'
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save()

    def reject(self, user, notes=''):
        self.status = 'rejected'
        self.resolution = 'rejected'
        self.resolution_notes = notes
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save()

    def resolve(self, resolution, refund_amount, notes, user, return_to_stock=False, mark_as_damaged=False):
        self.status = 'resolved'
        self.resolution = resolution
        self.refund_amount = refund_amount
        self.resolution_notes = notes
        self.return_to_stock = return_to_stock
        self.mark_as_damaged = mark_as_damaged
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save()