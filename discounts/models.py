from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal


class Discount(models.Model):
    """
    A discount rule that can be applied to a sale.
    Supports percentage off, fixed amount off, and buy-X-get-Y-free.
    Can be restricted to specific products, categories, or customer types.
    Can be time-limited or usage-capped.
    """

    # ── Discount types ────────────────────────────────────────────────────────
    TYPE_PERCENTAGE = 'percentage'
    TYPE_FIXED      = 'fixed'
    TYPE_BOGO       = 'bogo'       # Buy X get Y free

    TYPE_CHOICES = [
        (TYPE_PERCENTAGE, 'Percentage Off (%)'),
        (TYPE_FIXED,      'Fixed Amount Off (GH₵)'),
        (TYPE_BOGO,       'Buy X Get Y Free'),
    ]

    # ── Scope — what the discount applies to ─────────────────────────────────
    SCOPE_ALL        = 'all'        # Entire cart
    SCOPE_PRODUCT    = 'product'    # Specific product(s)
    SCOPE_CATEGORY   = 'category'  # Entire product category

    SCOPE_CHOICES = [
        (SCOPE_ALL,      'Entire Cart'),
        (SCOPE_PRODUCT,  'Specific Products'),
        (SCOPE_CATEGORY, 'Product Category'),
    ]

    # ── Customer restriction ──────────────────────────────────────────────────
    CUSTOMER_ALL       = 'all'
    CUSTOMER_RETAIL    = 'retail'
    CUSTOMER_WHOLESALE = 'wholesale'

    CUSTOMER_CHOICES = [
        (CUSTOMER_ALL,       'All Customers'),
        (CUSTOMER_RETAIL,    'Retail Only'),
        (CUSTOMER_WHOLESALE, 'Wholesale Only'),
    ]

    # ── Core fields ───────────────────────────────────────────────────────────
    name        = models.CharField(max_length=200)
    code        = models.CharField(
        max_length=50, unique=True, blank=True,
        help_text='Optional promo code. Leave blank for automatic discounts.'
    )
    description = models.TextField(blank=True)

    discount_type    = models.CharField(max_length=15, choices=TYPE_CHOICES, default=TYPE_PERCENTAGE)
    scope            = models.CharField(max_length=10, choices=SCOPE_CHOICES, default=SCOPE_ALL)
    customer_target  = models.CharField(max_length=10, choices=CUSTOMER_CHOICES, default=CUSTOMER_ALL)

    # ── Value fields ──────────────────────────────────────────────────────────
    value            = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text='Percentage (0-100) for % type, or GH₵ amount for fixed type.'
    )
    # BOGO fields
    buy_quantity     = models.PositiveIntegerField(default=1, help_text='Buy X …')
    get_quantity     = models.PositiveIntegerField(default=1, help_text='… get Y free')

    # ── Conditions ───────────────────────────────────────────────────────────
    minimum_amount   = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text='Minimum cart total for this discount to apply.'
    )
    maximum_discount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text='Cap the discount amount. 0 = no cap.'
    )

    # ── Scope targets ─────────────────────────────────────────────────────────
    products   = models.ManyToManyField(
        'products.Product', blank=True, related_name='discounts',
        help_text='Specific products this discount applies to (scope = product).'
    )
    categories = models.ManyToManyField(
        'products.Category', blank=True, related_name='discounts',
        help_text='Categories this discount applies to (scope = category).'
    )

    # ── Validity window ───────────────────────────────────────────────────────
    valid_from   = models.DateTimeField(default=timezone.now)
    valid_until  = models.DateTimeField(null=True, blank=True,
                                        help_text='Leave blank for no expiry.')

    # ── Usage limits ──────────────────────────────────────────────────────────
    usage_limit      = models.PositiveIntegerField(
        default=0, help_text='Max times this discount can be used total. 0 = unlimited.'
    )
    usage_limit_per_customer = models.PositiveIntegerField(
        default=0, help_text='Max times per customer. 0 = unlimited.'
    )
    times_used       = models.PositiveIntegerField(default=0)

    # ── Status ────────────────────────────────────────────────────────────────
    is_active    = models.BooleanField(default=True)
    requires_pin = models.BooleanField(
        default=False,
        help_text='Owner PIN must be entered before this discount can be applied.'
    )
    is_automatic = models.BooleanField(
        default=False,
        help_text='Auto-apply to every qualifying sale without a promo code.'
    )

    # ── Meta ──────────────────────────────────────────────────────────────────
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='discounts_created'
    )
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Discount'
        verbose_name_plural = 'Discounts'

    def __str__(self):
        return f'{self.name} ({self.get_discount_type_display()})'

    # ── Validity checks ───────────────────────────────────────────────────────

    @property
    def is_expired(self):
        if self.valid_until and timezone.now() > self.valid_until:
            return True
        return False

    @property
    def is_usage_exhausted(self):
        if self.usage_limit > 0 and self.times_used >= self.usage_limit:
            return True
        return False

    @property
    def is_currently_valid(self):
        return self.is_active and not self.is_expired and not self.is_usage_exhausted

    def is_valid_for_customer(self, customer):
        """Check customer type restriction."""
        if self.customer_target == self.CUSTOMER_ALL:
            return True
        if customer is None:
            return self.customer_target == self.CUSTOMER_RETAIL  # Walk-in = retail
        return customer.customer_type == self.customer_target

    def times_used_by(self, customer):
        """How many times has this specific customer used this discount."""
        if customer is None:
            return 0
        return self.usage_records.filter(customer=customer).count()

    def can_be_used_by(self, customer):
        """Full eligibility check for a specific customer."""
        if not self.is_currently_valid:
            return False, 'Discount is not currently active or has expired.'
        if not self.is_valid_for_customer(customer):
            return False, 'This discount is not available for this customer type.'
        if self.usage_limit_per_customer > 0:
            used = self.times_used_by(customer)
            if used >= self.usage_limit_per_customer:
                return False, 'This customer has reached the usage limit for this discount.'
        return True, ''

    # ── Calculation ───────────────────────────────────────────────────────────

    def calculate_discount_amount(self, subtotal, item_total=None):
        """
        Returns the GH₵ amount to deduct from the sale.
        subtotal  — full cart total before discount
        item_total — total of only the applicable items (for product/category scope)
        """
        base = item_total if item_total is not None else subtotal

        if subtotal < self.minimum_amount:
            return Decimal('0.00')

        if self.discount_type == self.TYPE_PERCENTAGE:
            amount = base * (self.value / Decimal('100'))
        elif self.discount_type == self.TYPE_FIXED:
            amount = min(self.value, base)
        else:
            # BOGO — caller (utils) handles unit logic; return 0 here
            return Decimal('0.00')

        # Apply cap
        if self.maximum_discount > 0:
            amount = min(amount, self.maximum_discount)

        return amount.quantize(Decimal('0.01'))


class DiscountUsage(models.Model):
    """
    One record per time a discount is applied to a completed sale.
    Powers per-customer usage limits and usage history.
    """
    discount    = models.ForeignKey(Discount, on_delete=models.CASCADE,
                                    related_name='usage_records')
    customer    = models.ForeignKey(
        'customers.Customer', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='discount_usages'
    )
    sale        = models.ForeignKey(
        'sales.Sale', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='discount_usages'
    )
    amount_saved = models.DecimalField(max_digits=12, decimal_places=2)
    applied_by   = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    applied_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-applied_at']
        verbose_name = 'Discount Usage'
        verbose_name_plural = 'Discount Usages'

    def __str__(self):
        return f'{self.discount.name} used on {self.applied_at:%Y-%m-%d} — saved GH₵{self.amount_saved}'