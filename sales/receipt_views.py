"""
sales/receipt_views.py

Screen receipt, thermal print layout, PDF download, warranty card PDF.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages

from accounts.decorators import owner_required
from .models import Sale, SaleItem
from .pdf_builder import build_receipt_pdf, build_warranty_card_pdf


@login_required
def download_receipt_pdf(request, pk):
    """Download the PDF receipt for a sale."""
    sale = get_object_or_404(Sale, pk=pk)
    if not request.user.is_owner and sale.attendant != request.user:
        messages.error(request, "You cannot access this receipt.")
        return redirect('sales:sale_list')
    return build_receipt_pdf(sale)


@login_required
def thermal_receipt(request, pk):
    """Thermal-optimised receipt view — for 58mm/80mm printers."""
    sale = get_object_or_404(Sale, pk=pk)
    if not request.user.is_owner and sale.attendant != request.user:
        messages.error(request, "You cannot access this receipt.")
        return redirect('sales:sale_list')
    items = sale.items.select_related('product')
    payments = sale.payments.all()

    cash_received = None
    if sale.payment_method == 'cash':
        cash_received = sale.total + sale.change_given
    elif sale.payment_method == 'split':
        cash_received = sum(
            (p.amount for p in payments if p.method == 'cash'), 0
        ) + sale.change_given

    try:
        from accounts.models import ShopProfile
        shop = ShopProfile.objects.first()
    except Exception:
        shop = None

    return __import__('django.shortcuts', fromlist=['render']).render(
        request,
        'sales/thermal_receipt.html',
        {'sale': sale, 'items': items, 'payments': payments, 'shop': shop,
         'cash_received': cash_received},
    )


@login_required
def download_warranty_card(request, item_pk):
    """Download warranty card PDF for a specific sale item."""
    item = get_object_or_404(SaleItem, pk=item_pk)
    if not request.user.is_owner and item.sale.attendant != request.user:
        messages.error(request, "You cannot access this warranty card.")
        return redirect('sales:sale_list')
    return build_warranty_card_pdf(item)