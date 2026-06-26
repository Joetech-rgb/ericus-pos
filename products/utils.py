from .models import Product, ProductUnit


def get_low_stock_products():
    """Return all active products that are at or below reorder point."""
    products = Product.objects.filter(is_active=True).select_related('category')
    return [p for p in products if p.is_low_stock]


def get_available_units(product):
    """Return sellable units for a product (in_stock, new condition)."""
    return ProductUnit.objects.filter(
        product=product,
        status='in_stock',
        condition__in=['new', 'refurb'],
    )


def get_demo_units(product):
    """Return demo/floor units for a product."""
    return ProductUnit.objects.filter(product=product, status='demo')


def product_stock_summary(product):
    """Return a dict with full stock breakdown for a product."""
    units = product.units.all()
    return {
        'in_stock':  units.filter(status='in_stock').count(),
        'sold':      units.filter(status='sold').count(),
        'demo':      units.filter(status='demo').count(),
        'returned':  units.filter(status='returned').count(),
        'damaged':   units.filter(status='damaged').count(),
        'reserved':  units.filter(status='reserved').count(),
        'total':     units.count(),
    }