"""
sales/utils.py

All the business logic for completing a sale:
- build_sale_from_cart()  — the main checkout function
- get_or_create_cart()    — cart management
- daily/period summaries  — for dashboard widgets
"""

from decimal import Decimal
from django.db import transaction
from django.utils import timezone


# ─── Cart Management ──────────────────────────────────────────────────────────

def get_or_create_cart(request):
    """Return the active CartSession for this user/session, creating one if needed."""
    from .models import CartSession

    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key

    cart = CartSession.objects.filter(session_key=session_key).first()

    if cart is None:
        cart = CartSession.objects.create(
            session_key=session_key,
            attendant=request.user,
        )
    elif cart.attendant != request.user:
        cart.attendant = request.user
        cart.save(update_fields=['attendant'])

    return cart


def clear_cart(request):
    """Delete the cart for this session (after completed sale)."""
    from .models import CartSession
    session_key = request.session.session_key
    CartSession.objects.filter(session_key=session_key).delete()


# ─── Checkout ─────────────────────────────────────────────────────────────────

@transaction.atomic
def build_sale_from_cart(cart, payment_method, cash_tendered=None,
                          momo_amount=None, momo_reference='',
                          credit_due_date=None, user=None):
    """
    The main checkout function. Takes a CartSession and payment details,
    creates Sale + SaleItems + Payments, deducts stock, and returns the Sale.

    Raises ValueError for any business rule violation.
    """
    from .models import Sale, SaleItem, Payment
    from inventory.utils import record_movement
    from customers.models import Customer

    if not cart.items_json:
        raise ValueError("Cart is empty.")

    sale_type = cart.sale_type or 'retail'
    total = cart.total

    # ── Validate payment amounts ──────────────────────────────────────────────
    cash_tendered = Decimal(str(cash_tendered or 0))
    momo_amount = Decimal(str(momo_amount or 0))

    if payment_method == 'cash':
        if cash_tendered < total:
            raise ValueError(
                f"Cash tendered (GH₵{cash_tendered}) is less than total (GH₵{total})."
            )
        change = cash_tendered - total
        amount_paid = total
    elif payment_method == 'momo':
        if momo_amount < total:
            raise ValueError(
                f"MoMo amount (GH₵{momo_amount}) is less than total (GH₵{total})."
            )
        change = Decimal('0')
        amount_paid = total
    elif payment_method == 'split':
        amount_paid = cash_tendered + momo_amount
        if amount_paid < total:
            raise ValueError(
                f"Total paid (GH₵{amount_paid}) is less than total (GH₵{total})."
            )
        change = amount_paid - total
    elif payment_method == 'credit':
        if not cart.customer:
            raise ValueError("Credit sales require a customer to be selected.")
        customer = cart.customer
        if customer.is_over_credit_limit:
            raise ValueError(
                f"{customer.full_name} has exceeded their credit limit. "
                f"Outstanding: GH₵{customer.credit_balance}, Limit: GH₵{customer.credit_limit}."
            )
        amount_paid = Decimal('0')
        change = Decimal('0')
    else:
        raise ValueError(f"Unknown payment method: {payment_method}")

    # ── Create the Sale ───────────────────────────────────────────────────────
    # NOTE: Sale.save() automatically sets locked=True and generates receipt_number.
    # Do NOT pass locked=False or mutate Sale.locked.field — it is unnecessary and
    # causes a global class-level side effect that breaks subsequent sales.
    sale = Sale(
        attendant=user,
        customer=cart.customer,
        sale_type=sale_type,
        subtotal=cart.subtotal,
        discount_amount=cart.discount_amount,
        discount=cart.discount,
        discount_code_used=cart.discount_code,
        installation_fee=cart.installation_fee,
        delivery_fee=cart.delivery_fee,
        total=total,
        payment_method=payment_method,
        amount_paid=amount_paid,
        change_given=change,
        is_credit=(payment_method == 'credit'),
        credit_due_date=credit_due_date if payment_method == 'credit' else None,
        notes=cart.notes,
    )
    sale.save()  # Sale.save() handles receipt_number and locked=True automatically

    # ── Create SaleItems and deduct stock ─────────────────────────────────────
    from products.models import Product, ProductUnit

    for item in cart.items_json:
        product = Product.objects.select_for_update().get(pk=item['product_id'])
        product_unit = None
        if item.get('product_unit_id'):
            product_unit = ProductUnit.objects.get(pk=item['product_unit_id'])

        sale_item = SaleItem(
            sale=sale,
            product=product,
            product_unit=product_unit,
            quantity=item['quantity'],
            unit_price=Decimal(str(item['unit_price'])),
            cost_price=Decimal(str(item['cost_price'])),
        )
        sale_item.save()

        # Deduct inventory
        record_movement(
            product=product,
            movement_type='sale',
            quantity=item['quantity'],
            user=user,
            reference_type='sale',
            reference_id=sale.pk,
            reference_label=sale.receipt_number,
            serial_number=item.get('serial_number', ''),
            note=f"Sale {sale.receipt_number}",
        )

        # Mark unit as sold
        if product_unit:
            product_unit.mark_sold()

    # ── Create Payment records ────────────────────────────────────────────────
    if payment_method == 'cash':
        Payment.objects.create(sale=sale, method='cash', amount=total)
    elif payment_method == 'momo':
        Payment.objects.create(sale=sale, method='momo', amount=total,
                                momo_reference=momo_reference)
    elif payment_method == 'split':
        if cash_tendered > 0:
            Payment.objects.create(sale=sale, method='cash', amount=cash_tendered - change)
        if momo_amount > 0:
            Payment.objects.create(sale=sale, method='momo', amount=momo_amount,
                                    momo_reference=momo_reference)
    elif payment_method == 'credit':
        Payment.objects.create(sale=sale, method='credit', amount=Decimal('0'))
        # Add to customer debt
        cart.customer.add_credit(total)

    # ── Award loyalty points ──────────────────────────────────────────────────
    if cart.customer and payment_method != 'credit':
        try:
            from customers.utils import award_loyalty_points
            award_loyalty_points(cart.customer, total)
        except Exception:
            pass  # Loyalty points are non-critical

    # ── Log discount usage ────────────────────────────────────────────────────
    if cart.discount:
        try:
            from discounts.utils import apply_discount_to_sale
            apply_discount_to_sale(cart.discount, cart.customer, sale, cart.discount_amount, user)
        except Exception:
            pass

    return sale


# ─── Sale Summary Helpers ──────────────────────────────────────────────────────

def get_daily_summary(date=None):
    """Sales summary for a given date (defaults to today)."""
    from django.db.models import Sum, Count, Q
    from .models import Sale, Payment

    date = date or timezone.now().date()
    sales = Sale.objects.filter(created_at__date=date)

    payments = Payment.objects.filter(sale__created_at__date=date)

    result = sales.aggregate(
        total_sales=Count('id'),
        total_revenue=Sum('total'),
        total_discount=Sum('discount_amount'),
        cash_sales=Sum('total', filter=Q(payment_method='cash')),
        momo_sales=Sum('total', filter=Q(payment_method='momo')),
        split_sales=Sum('total', filter=Q(payment_method='split')),
        credit_sales=Sum('total', filter=Q(payment_method='credit')),
    )

    for key in result:
        if result[key] is None:
            result[key] = Decimal('0')

    result['date'] = date
    return result


def get_period_summary(date_from, date_to):
    """Sales summary for a date range."""
    from django.db.models import Sum, Count, Q
    from .models import Sale

    sales = Sale.objects.filter(created_at__date__gte=date_from, created_at__date__lte=date_to)
    result = sales.aggregate(
        total_sales=Count('id'),
        total_revenue=Sum('total'),
        total_discount=Sum('discount_amount'),
        cash_sales=Sum('total', filter=Q(payment_method='cash')),
        momo_sales=Sum('total', filter=Q(payment_method='momo')),
        split_sales=Sum('total', filter=Q(payment_method='split')),
        credit_sales=Sum('total', filter=Q(payment_method='credit')),
    )
    for key in result:
        if result[key] is None:
            result[key] = Decimal('0')
    return result


def get_top_selling_products(date_from=None, date_to=None, limit=10):
    """Top products by quantity sold in a period."""
    from django.db.models import Sum
    from .models import SaleItem

    qs = SaleItem.objects.all()
    if date_from:
        qs = qs.filter(sale__created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(sale__created_at__date__lte=date_to)

    return (
        qs.values('product_id', 'product_name', 'product_brand')
        .annotate(
            total_qty=Sum('quantity'),
            total_revenue=Sum('subtotal'),
        )
        .order_by('-total_qty')[:limit]
    )


def get_attendant_performance(date_from=None, date_to=None):
    """Sales breakdown per attendant for a period."""
    from django.db.models import Sum, Count
    from .models import Sale

    qs = Sale.objects.all()
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    return (
        qs.values('attendant_id', 'attendant_username')
        .annotate(
            total_sales=Count('id'),
            total_revenue=Sum('total'),
            total_discount=Sum('discount_amount'),
        )
        .order_by('-total_revenue')
    )


def get_recent_sales(limit=10):
    """Most recent sales for dashboard feed."""
    from .models import Sale
    return (
        Sale.objects
        .select_related('attendant', 'customer')
        .prefetch_related('items')
        .order_by('-created_at')[:limit]
    )


def get_cash_position(date=None):
    """
    Expected cash in till for a given date.
    Cash from sales minus change given.
    """
    from django.db.models import Sum
    from .models import Payment, Sale

    date = date or timezone.now().date()
    cash_in = (
        Payment.objects
        .filter(sale__created_at__date=date, method='cash')
        .aggregate(total=Sum('amount'))['total'] or Decimal('0')
    )
    change_out = (
        Sale.objects
        .filter(created_at__date=date, payment_method__in=['cash', 'split'])
        .aggregate(total=Sum('change_given'))['total'] or Decimal('0')
    )
    return cash_in - change_out