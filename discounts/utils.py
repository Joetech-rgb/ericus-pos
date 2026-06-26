from decimal import Decimal
from django.db import models as _django_models
from django.utils import timezone
from .models import Discount, DiscountUsage


def get_discount_by_code(code):
    """
    Look up a discount by promo code (case-insensitive).
    Returns the Discount object or None.
    """
    try:
        return Discount.objects.get(code__iexact=code.strip(), is_active=True)
    except Discount.DoesNotExist:
        return None


def get_automatic_discounts():
    """
    Return all active automatic discounts valid right now.
    The POS checks these on every sale without needing a promo code.
    """
    return Discount.objects.filter(
        is_active=True,
        is_automatic=True,
        valid_from__lte=timezone.now(),
    ).filter(
        _django_models.Q(valid_until__isnull=True) | _django_models.Q(valid_until__gte=timezone.now())
    )


def validate_discount(discount, cart_total, customer=None):
    """
    Full validation of a discount against the current cart.

    Returns:
        (is_valid: bool, error_message: str, discount_amount: Decimal)
    """
    can_use, reason = discount.can_be_used_by(customer)
    if not can_use:
        return False, reason, Decimal('0.00')

    if cart_total < discount.minimum_amount:
        return (
            False,
            f'Minimum purchase of GH\u20b5{discount.minimum_amount} required for this discount.',
            Decimal('0.00'),
        )

    amount = discount.calculate_discount_amount(cart_total)
    return True, '', amount


def apply_discount_to_sale(discount, sale, customer, amount_saved, applied_by):
    """
    Record a discount usage after a sale is completed.
    Increments the global usage counter.
    Call this ONCE per sale, after the sale is saved.
    """
    DiscountUsage.objects.create(
        discount=discount,
        customer=customer,
        sale=sale,
        amount_saved=amount_saved,
        applied_by=applied_by,
    )
    Discount.objects.filter(pk=discount.pk).update(times_used=discount.times_used + 1)


def calculate_item_total_for_scope(discount, sale_items):
    """
    For product- or category-scoped discounts, sum only the applicable items.
    sale_items — iterable of dicts with keys: product_id, category_id, line_total
    Returns Decimal total of matching items, or None for SCOPE_ALL.
    """
    if discount.scope == Discount.SCOPE_ALL:
        return None  # Signal to caller: use the full cart total

    applicable_product_ids  = set(discount.products.values_list('id', flat=True))
    applicable_category_ids = set(discount.categories.values_list('id', flat=True))

    total = Decimal('0.00')
    for item in sale_items:
        if discount.scope == Discount.SCOPE_PRODUCT:
            if item.get('product_id') in applicable_product_ids:
                total += item.get('line_total', Decimal('0.00'))
        elif discount.scope == Discount.SCOPE_CATEGORY:
            if item.get('category_id') in applicable_category_ids:
                total += item.get('line_total', Decimal('0.00'))

    return total


def get_bogo_free_quantity(discount, item_quantity):
    """
    For BOGO discounts, calculate how many units are free.
    e.g. Buy 2 get 1 free, 5 items => 2 sets of (2+1), remainder 2 > buy_qty so 0 extra.
    Result: 2 free units.
    """
    if discount.discount_type != Discount.TYPE_BOGO:
        return 0
    buy  = discount.buy_quantity
    get  = discount.get_quantity
    sets = item_quantity // (buy + get)
    remainder  = item_quantity % (buy + get)
    extra_free = max(0, remainder - buy)
    return (sets * get) + extra_free


def get_discount_summary():
    """Dashboard stats for the discount widget."""
    from django.db.models import Sum
    now = timezone.now()
    active = Discount.objects.filter(is_active=True)
    return {
        'total_active':   active.count(),
        'expiring_soon':  active.filter(
                              valid_until__isnull=False,
                              valid_until__lte=now + timezone.timedelta(days=7)
                          ).count(),
        'total_savings':  DiscountUsage.objects.aggregate(t=Sum('amount_saved'))['t'] or Decimal('0.00'),
        'total_used':     DiscountUsage.objects.count(),
    }