from django.db import transaction
from django.db.models import Sum, Count, Q
from datetime import date


@transaction.atomic
def process_return_resolution(return_obj, user):
    """
    After a Return is resolved:
    - Move stock back if return_to_stock is True
    - Log as damaged if mark_as_damaged is True
    - Adjust customer credit if resolution is store_credit
    - Log to audit trail
    """
    from inventory.utils import record_movement
    from audit.utils import log_return

    if return_obj.return_to_stock and not return_obj.mark_as_damaged:
        record_movement(
            product=return_obj.product,
            movement_type='return',
            quantity=return_obj.quantity,
            reference=return_obj,
            notes=f"Return {return_obj.return_number} — returned to sellable stock",
            user=user,
        )

    elif return_obj.mark_as_damaged:
        record_movement(
            product=return_obj.product,
            movement_type='damaged',
            quantity=return_obj.quantity,
            reference=return_obj,
            notes=f"Return {return_obj.return_number} — logged as damaged",
            user=user,
        )

    # If store credit, add to customer balance
    if return_obj.resolution == 'store_credit' and return_obj.customer:
        return_obj.customer.add_credit(return_obj.net_refund)

    log_return(
        user,
        f"Resolved return {return_obj.return_number}: {return_obj.get_resolution_display()} "
        f"— GH₵{return_obj.net_refund} net refund",
        obj=return_obj,
    )


def get_return_summary():
    """Dashboard summary stats for returns."""
    today = date.today()
    month_start = today.replace(day=1)

    total_returns = Return.objects.count()
    pending_returns = Return.objects.filter(status='pending').count()
    month_refunds = Return.objects.filter(
        status='resolved',
        return_date__gte=month_start,
    ).aggregate(total=Sum('refund_amount'))['total'] or 0

    return {
        'total_returns': total_returns,
        'pending_returns': pending_returns,
        'month_refunds': month_refunds,
    }


def get_recent_returns(limit=10):
    from .models import Return
    return Return.objects.select_related(
        'product', 'customer', 'processed_by'
    ).order_by('-created_at')[:limit]


def get_return_reasons_breakdown():
    """For reports — count by reason."""
    from .models import Return
    return Return.objects.values('reason').annotate(
        count=Count('id'),
        total_refunded=Sum('refund_amount'),
    ).order_by('-count')


def get_pending_returns():
    from .models import Return
    return Return.objects.filter(status='pending').select_related(
        'product', 'customer', 'processed_by'
    ).order_by('-created_at')


# Avoid circular import at top level
from .models import Return