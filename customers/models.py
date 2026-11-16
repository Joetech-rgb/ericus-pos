from django.db import models
from django.conf import settings
from django.utils import timezone


class Customer(models.Model):
    """
    A customer of Adjei’s God First Ventures.
    Linked to sales, wholesale orders, and returns.
    """

    # ── Customer type ─────────────────────────────────────────────────────────
    TYPE_RETAIL    = 'retail'
    TYPE_WHOLESALE = 'wholesale'
    TYPE_CHOICES   = [
        (TYPE_RETAIL,    'Retail'),
        (TYPE_WHOLESALE, 'Wholesale'),
    ]

    # ── Basic info ────────────────────────────────────────────────────────────
    full_name    = models.CharField(max_length=200)
    phone        = models.CharField(max_length=20, unique=True)
    phone_alt    = models.CharField(max_length=20, blank=True)
    email        = models.EmailField(blank=True)
    company_name = models.CharField(max_length=200, blank=True,
                                    help_text='For wholesale / business customers')
    address      = models.TextField(blank=True)
    customer_type = models.CharField(
        max_length=10, choices=TYPE_CHOICES, default=TYPE_RETAIL, db_index=True
    )

    # ── Credit / loyalty ──────────────────────────────────────────────────────
    credit_limit  = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    credit_balance = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text='Positive = customer owes us; Negative = we owe customer (overpayment)'
    )
    loyalty_points = models.PositiveIntegerField(default=0)

    # ── Meta ──────────────────────────────────────────────────────────────────
    notes      = models.TextField(blank=True)
    is_active  = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='customers_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['full_name']
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'
        indexes = [
            models.Index(fields=['phone']),
            models.Index(fields=['customer_type', 'is_active']),
        ]

    def __str__(self):
        if self.company_name:
            return f'{self.full_name} ({self.company_name})'
        return self.full_name

    # ── Computed properties ───────────────────────────────────────────────────

    @property
    def display_name(self):
        return self.company_name or self.full_name

    @property
    def is_over_credit_limit(self):
        return self.credit_balance > self.credit_limit

    @property
    def available_credit(self):
        """How much more the customer can owe before hitting the limit."""
        return max(self.credit_limit - self.credit_balance, 0)

    @property
    def total_purchases(self):
        """Sum of all sale totals for this customer."""
        from django.db.models import Sum
        # FIX: removed filter(status='completed') — Sale has no status field
        result = self.sales.aggregate(t=Sum('total'))
        return result['t'] or 0

    @property
    def total_transactions(self):
        # FIX: removed filter(status='completed') — Sale has no status field
        return self.sales.count()

    @property
    def last_purchase_date(self):
        # FIX: removed filter(status='completed') — Sale has no status field
        sale = self.sales.order_by('-created_at').first()
        return sale.created_at if sale else None

    # ── Credit helpers ────────────────────────────────────────────────────────

    def add_credit(self, amount):
        """Customer owes more (e.g. bought on credit)."""
        self.credit_balance += amount
        self.save(update_fields=['credit_balance', 'updated_at'])

    def reduce_credit(self, amount):
        """Customer paid back some credit."""
        self.credit_balance -= amount
        self.save(update_fields=['credit_balance', 'updated_at'])

    def add_loyalty_points(self, points):
        self.loyalty_points += points
        self.save(update_fields=['loyalty_points', 'updated_at'])

    def redeem_loyalty_points(self, points):
        if points > self.loyalty_points:
            raise ValueError('Insufficient loyalty points')
        self.loyalty_points -= points
        self.save(update_fields=['loyalty_points', 'updated_at'])


class CreditPayment(models.Model):
    """
    Records a payment made by a customer to reduce their credit balance.
    Keeps a full history of every credit settlement.
    """

    PAYMENT_CASH   = 'cash'
    PAYMENT_MOMO   = 'momo'
    PAYMENT_BANK   = 'bank'
    PAYMENT_CHOICES = [
        (PAYMENT_CASH, 'Cash'),
        (PAYMENT_MOMO, 'Mobile Money (MoMo)'),
        (PAYMENT_BANK, 'Bank Transfer'),
    ]

    customer       = models.ForeignKey(Customer, on_delete=models.CASCADE,
                                       related_name='credit_payments')
    amount         = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_CHOICES,
                                      default=PAYMENT_CASH)
    reference      = models.CharField(max_length=100, blank=True,
                                      help_text='MoMo transaction ID or bank reference')
    note           = models.TextField(blank=True)
    recorded_by    = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='credit_payments_recorded'
    )
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Credit Payment'
        verbose_name_plural = 'Credit Payments'

    def __str__(self):
        return f'{self.customer} — GH₵{self.amount} on {self.created_at:%Y-%m-%d}'