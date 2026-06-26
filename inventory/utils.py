"""
inventory/utils.py

Central helpers for recording stock movements and querying stock health.
All stock changes anywhere in the project should go through record_movement()
so every change is logged automatically.
"""

from django.db import transaction
from django.utils import timezone


def record_movement(
    product,
    movement_type,
    quantity,
    user=None,
    note='',
    reference_type='',
    reference_id=None,
    reference_label='',
    serial_number='',
):
    """
    The single function every app calls to change stock.

    Creates a StockMovement entry and updates StockLevel atomically.
    Returns the StockMovement instance.

    movement_type must be one of StockMovement.MOVEMENT_TYPES keys.
    quantity must be positive — direction is inferred from movement_type.
    """
    from inventory.models import StockLevel, StockMovement

    INBOUND = StockMovement.INBOUND_TYPES
    OUTBOUND = StockMovement.OUTBOUND_TYPES

    if quantity <= 0:
        raise ValueError("Quantity must be positive.")

    valid_types = {t[0] for t in StockMovement.MOVEMENT_TYPES}
    if movement_type not in valid_types:
        raise ValueError(f"Invalid movement_type: {movement_type}")

    with transaction.atomic():
        # Get or create the stock level record
        stock_level, _ = StockLevel.objects.select_for_update().get_or_create(
            product=product,
            defaults={'quantity': 0, 'last_updated_by': user},
        )

        qty_before = stock_level.quantity

        if movement_type in INBOUND:
            stock_level.quantity += quantity
        elif movement_type in OUTBOUND:
            if quantity > stock_level.quantity:
                raise ValueError(
                    f"Insufficient stock for {product.name}. "
                    f"Available: {stock_level.quantity}, Requested: {quantity}"
                )
            stock_level.quantity -= quantity
        # 'count' and 'transfer' are handled differently — caller sets qty_after directly

        stock_level.last_updated_by = user
        stock_level.save()

        qty_after = stock_level.quantity

        movement = StockMovement(
            product=product,
            movement_type=movement_type,
            quantity=quantity,
            quantity_before=qty_before,
            quantity_after=qty_after,
            reference_type=reference_type,
            reference_id=reference_id,
            reference_label=reference_label,
            serial_number=serial_number,
            note=note,
            created_by=user,
            created_by_username=user.username if user else '',
        )
        movement.save()

    return movement


def set_stock_count(product, new_quantity, user, note='Stock count correction'):
    """
    Hard-set stock to a specific value (physical count result).
    Records a 'count' movement showing the adjustment.
    Returns the StockMovement.
    """
    from inventory.models import StockLevel, StockMovement

    if new_quantity < 0:
        raise ValueError("Stock quantity cannot be negative.")

    with transaction.atomic():
        stock_level, _ = StockLevel.objects.select_for_update().get_or_create(
            product=product,
            defaults={'quantity': 0},
        )
        qty_before = stock_level.quantity
        adjustment = abs(new_quantity - qty_before)

        stock_level.quantity = new_quantity
        stock_level.last_updated_by = user
        stock_level.save()

        movement = StockMovement(
            product=product,
            movement_type='count',
            quantity=adjustment if adjustment > 0 else 0,
            quantity_before=qty_before,
            quantity_after=new_quantity,
            note=note,
            created_by=user,
            created_by_username=user.username if user else '',
        )
        movement.save()

    return movement


def get_low_stock_products():
    """Returns products whose current stock is at or below their reorder point."""
    from inventory.models import StockLevel
    return (
        StockLevel.objects
        .select_related('product', 'product__category')
        .filter(quantity__lte=models_reorder_point())
        .order_by('quantity')
    )


def models_reorder_point():
    """Helper — returns an F() expression for product reorder_point."""
    from django.db.models import F
    return F('product__reorder_point')


def get_low_stock_list():
    """Returns queryset of StockLevel objects where qty <= reorder_point."""
    from django.db.models import F
    from inventory.models import StockLevel
    return (
        StockLevel.objects
        .select_related('product', 'product__category')
        .filter(quantity__lte=F('product__reorder_point'))
        .order_by('quantity')
    )


def get_out_of_stock_list():
    """Returns all products with zero stock."""
    from inventory.models import StockLevel
    return (
        StockLevel.objects
        .select_related('product', 'product__category')
        .filter(quantity=0)
        .order_by('product__name')
    )


def get_stock_summary():
    """
    Dashboard widget: total products, low stock count, out of stock count,
    total units in stock, total stock value.
    """
    from django.db.models import F, Sum, Count, Q
    from inventory.models import StockLevel

    qs = StockLevel.objects.select_related('product')

    totals = qs.aggregate(
        total_products=Count('id'),
        total_units=Sum('quantity'),
        out_of_stock=Count('id', filter=Q(quantity=0)),
        low_stock=Count('id', filter=Q(quantity__gt=0, quantity__lte=F('product__reorder_point'))),
    )

    # Stock value = sum of qty * cost_price
    value_qs = qs.aggregate(
        total_value=Sum(F('quantity') * F('product__cost_price'))
    )

    totals['total_value'] = value_qs['total_value'] or 0
    totals['total_units'] = totals['total_units'] or 0
    return totals


def get_product_movement_history(product, limit=50):
    """Returns the last N movements for a given product."""
    from inventory.models import StockMovement
    return (
        StockMovement.objects
        .filter(product=product)
        .select_related('created_by')
        .order_by('-created_at')[:limit]
    )


def get_recent_movements(limit=20):
    """Returns the most recent stock movements across all products."""
    from inventory.models import StockMovement
    return (
        StockMovement.objects
        .select_related('product', 'product__category', 'created_by')
        .order_by('-created_at')[:limit]
    )


def get_active_demo_units():
    """Returns all current floor/demo units."""
    from inventory.models import DemoUnit
    return (
        DemoUnit.objects
        .filter(is_active=True)
        .select_related('product', 'product__category', 'converted_by')
        .order_by('-converted_at')
    )


def create_demo_unit(product_unit, user):
    """
    Convert a ProductUnit to a demo unit.
    Deducts it from sellable stock and logs a 'demo' movement.
    product_unit is a products.ProductUnit instance.
    """
    from inventory.models import DemoUnit

    with transaction.atomic():
        record_movement(
            product=product_unit.product,
            movement_type='demo',
            quantity=1,
            user=user,
            note=f"Unit {product_unit.serial_number} moved to floor display",
            serial_number=product_unit.serial_number,
        )
        product_unit.convert_to_demo()  # marks the unit as demo in products app

        demo = DemoUnit.objects.create(
            product=product_unit.product,
            serial_number=product_unit.serial_number,
            converted_by=user,
        )
    return demo


def return_demo_to_stock(demo_unit, user, note=''):
    """
    Return a floor demo unit back to sellable stock.
    Adds it back to stock and logs a 'demo_to_stock' movement.
    """
    with transaction.atomic():
        record_movement(
            product=demo_unit.product,
            movement_type='demo_to_stock',
            quantity=1,
            user=user,
            note=note or f"Demo unit {demo_unit.serial_number} returned to sellable stock",
            serial_number=demo_unit.serial_number,
        )
        demo_unit.return_to_stock(user)


def generate_audit_reference():
    """Generate a unique stock audit reference number e.g. AUDIT-2025-007."""
    from inventory.models import StockAudit
    year = timezone.now().year
    count = StockAudit.objects.filter(started_at__year=year).count() + 1
    return f"AUDIT-{year}-{count:03d}"


def complete_stock_audit(audit, user):
    """
    Finalise a stock audit:
    - Apply stock count corrections for all items with discrepancies
    - Mark audit as completed
    """
    from inventory.models import StockAuditItem

    if audit.status != 'open':
        raise ValueError("Only open audits can be completed.")

    with transaction.atomic():
        for item in audit.items.filter(has_discrepancy=True):
            set_stock_count(
                product=item.product,
                new_quantity=item.physical_count,
                user=user,
                note=f"Stock audit {audit.reference} — physical count correction",
            )
        audit.status = 'completed'
        audit.completed_at = timezone.now()
        audit.save()