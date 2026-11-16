from django.db.models import Sum, Count
from datetime import date


def get_wholesale_summary():
    """Dashboard summary stats."""
    from .models import WholesaleOrder
    today = date.today()
    month_start = today.replace(day=1)

    total_orders = WholesaleOrder.objects.count()
    pending_orders = WholesaleOrder.objects.filter(
        status__in=['draft', 'confirmed', 'packed']
    ).count()
    month_revenue = WholesaleOrder.objects.filter(
        status='delivered',
        delivery_date__gte=month_start,
    ).aggregate(total=Sum('grand_total'))['total'] or 0
    outstanding = WholesaleOrder.objects.filter(
        payment_status__in=['unpaid', 'partial']
    ).aggregate(total=Sum('grand_total') - Sum('amount_paid'))['total'] or 0

    return {
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'month_revenue': month_revenue,
        'outstanding': max(0, outstanding),
    }


def get_recent_wholesale_orders(limit=10):
    from .models import WholesaleOrder
    return WholesaleOrder.objects.select_related(
        'customer', 'created_by'
    ).order_by('-created_at')[:limit]


def get_top_wholesale_customers(limit=10):
    from .models import WholesaleOrder
    return WholesaleOrder.objects.filter(
        status='delivered'
    ).values(
        'customer__id', 'customer__full_name', 'customer__phone'
    ).annotate(
        order_count=Count('id'),
        total_spent=Sum('grand_total'),
    ).order_by('-total_spent')[:limit]


def process_wholesale_delivery(order, user):
    """
    Mark order as delivered and record stock movements for each item.
    Called atomically from the view.
    """
    from django.db import transaction
    from inventory.utils import record_movement
    from audit.utils import log_wholesale

    with transaction.atomic():
        for item in order.items.select_related('product'):
            record_movement(
                product=item.product,
                movement_type='sale',
                quantity=item.quantity,
                reference=order,
                notes=f"Wholesale order {order.order_number}",
                user=user,
            )
        order.status = 'delivered'
        order.delivery_date = date.today()
        order.save()

        log_wholesale(
            user,
            f"Delivered wholesale order {order.order_number} to {order.customer.full_name}",
            obj=order,
        )
