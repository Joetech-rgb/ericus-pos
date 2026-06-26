from django.db.models import Sum, Count, Q
from .models import Customer, CreditPayment


def get_customer_summary():
    """
    High-level stats for the dashboard widget.
    Returns a dict — no heavy queries, single aggregation pass.
    """
    qs = Customer.objects.filter(is_active=True)
    agg = qs.aggregate(
        total=Count('id'),
        retail=Count('id', filter=Q(customer_type=Customer.TYPE_RETAIL)),
        wholesale=Count('id', filter=Q(customer_type=Customer.TYPE_WHOLESALE)),
        with_balance=Count('id', filter=Q(credit_balance__gt=0)),
        total_outstanding=Sum('credit_balance'),
    )
    return {
        'total':            agg['total'] or 0,
        'retail':           agg['retail'] or 0,
        'wholesale':        agg['wholesale'] or 0,
        'with_balance':     agg['with_balance'] or 0,
        'total_outstanding': agg['total_outstanding'] or 0,
    }


def get_top_customers(limit=10):
    """
    Returns customers ordered by total completed purchase amount.
    Used in reports.
    """
    return (
        Customer.objects
        .filter(is_active=True)
        .annotate(total_spent=Sum('sales__total_amount', filter=Q(sales__status='completed')))
        .order_by('-total_spent')[:limit]
    )


def get_customers_with_outstanding_credit():
    """All active customers who still owe money."""
    return (
        Customer.objects
        .filter(is_active=True, credit_balance__gt=0)
        .order_by('-credit_balance')
    )


def award_loyalty_points(customer, sale_amount):
    """
    Award 1 loyalty point per GH₵10 spent.
    Call this after a completed sale is saved.
    """
    points = int(sale_amount // 10)
    if points > 0:
        customer.add_loyalty_points(points)
    return points


def get_or_create_walk_in():
    """
    Returns the special 'Walk-in Customer' record.
    Created once and reused for all anonymous retail sales.
    """
    customer, _ = Customer.objects.get_or_create(
        phone='0000000000',
        defaults={
            'full_name':     'Walk-in Customer',
            'customer_type': Customer.TYPE_RETAIL,
            'is_active':     True,
        },
    )
    return customer