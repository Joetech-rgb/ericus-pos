from django.db import transaction
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import date, timedelta

from .models import PurchaseOrder, PurchaseOrderItem, GoodsReceivedNote, GRNItem


@transaction.atomic
def receive_grn(grn, grn_item_data, received_by):
    """
    Process a Goods Received Note.
    grn_item_data = list of dicts:
        {'po_item_id': int, 'quantity_received': int, 'condition': str, 'notes': str}

    - Creates GRNItem records
    - Updates PurchaseOrderItem.quantity_received
    - Calls inventory.utils.record_movement() for each line
    - Updates PO status
    - Returns the saved GRN
    """
    from inventory.utils import record_movement
    from products.models import ProductUnit

    total_received = 0

    for item_data in grn_item_data:
        qty = item_data.get('quantity_received', 0)
        if qty <= 0:
            continue

        po_item = PurchaseOrderItem.objects.select_related('product').get(
            pk=item_data['po_item_id'],
            purchase_order=grn.purchase_order
        )

        condition = item_data.get('condition', 'new')

        # Create GRN item record
        GRNItem.objects.create(
            grn=grn,
            po_item=po_item,
            quantity_received=qty,
            condition=condition,
            notes=item_data.get('notes', ''),
        )

        # Update PO item received count
        po_item.quantity_received = (po_item.quantity_received or 0) + qty
        po_item.save(update_fields=['quantity_received'])

        # Record stock movement (inventory app)
        if condition == 'new':
            movement_type = 'purchase'
        else:
            movement_type = 'damaged'

        record_movement(
            product=po_item.product,
            movement_type=movement_type,
            quantity=qty,
            reference=grn,
            notes=f"GRN {grn.grn_number} — PO {grn.purchase_order.po_number}",
            user=received_by,
        )

        # Update the product's cost price if this is a new cost
        if condition == 'new' and po_item.unit_cost > 0:
            po_item.product.cost_price = po_item.unit_cost
            po_item.product.save(update_fields=['cost_price'])

        total_received += qty

    # Update PO status
    grn.purchase_order.update_status_from_items()

    return grn


def get_purchase_summary():
    """Dashboard summary stats."""
    today = date.today()
    month_start = today.replace(day=1)

    total_pos = PurchaseOrder.objects.count()
    pending_pos = PurchaseOrder.objects.filter(
        status__in=['draft', 'ordered', 'partial']
    ).count()

    month_total = PurchaseOrder.objects.filter(
        status='received',
        received_date__gte=month_start,
    ).aggregate(total=Sum('grand_total'))['total'] or 0

    amount_owed = PurchaseOrder.objects.filter(
        status__in=['ordered', 'partial', 'received'],
    ).aggregate(
        owed=Sum('grand_total') - Sum('amount_paid')
    )['owed'] or 0

    return {
        'total_pos': total_pos,
        'pending_pos': pending_pos,
        'month_total': month_total,
        'amount_owed': max(0, amount_owed),
    }


def get_recent_purchase_orders(limit=10):
    return PurchaseOrder.objects.select_related(
        'supplier', 'created_by'
    ).order_by('-created_at')[:limit]


def get_supplier_summary():
    """Top suppliers by total spend."""
    from .models import Supplier
    return Supplier.objects.filter(
        is_active=True
    ).annotate(
        order_count=Count('purchaseorder'),
        total_spend=Sum('purchaseorder__grand_total'),
    ).order_by('-total_spend')[:10]


def get_monthly_purchase_trend(months=6):
    """Returns list of {label, total} for the last N months."""
    results = []
    today = date.today()
    for i in range(months - 1, -1, -1):
        # Go back i months
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1)
        else:
            month_end = date(year, month + 1, 1)

        total = PurchaseOrder.objects.filter(
            status='received',
            received_date__gte=month_start,
            received_date__lt=month_end,
        ).aggregate(total=Sum('grand_total'))['total'] or 0

        results.append({
            'label': month_start.strftime('%b %Y'),
            'total': float(total),
        })
    return results


def get_outstanding_payables():
    """All POs with money still owed."""
    return PurchaseOrder.objects.filter(
        status__in=['ordered', 'partial', 'received'],
    ).exclude(
        amount_paid__gte=models_grand_total_annotation()
    ).select_related('supplier').order_by('order_date')


def models_grand_total_annotation():
    """Helper to reference grand_total in filter."""
    from django.db.models import F
    return F('grand_total')


def get_pending_pos_for_dashboard():
    """Returns draft/ordered POs for dashboard alert."""
    return PurchaseOrder.objects.filter(
        status__in=['draft', 'ordered']
    ).select_related('supplier').order_by('-created_at')[:5]