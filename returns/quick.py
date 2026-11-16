"""
returns/quick.py - the simple one-screen Returns flow.
"""
from decimal import Decimal

from django.contrib import messages
from django.db import transaction
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from accounts.decorators import owner_required, attendant_required
from audit.utils import log_return
from .models import Return

REASONS = [
    ('defective', 'Not working / faulty'),
    ('wrong_item', 'Wrong item'),
    ('customer_change_mind', 'Customer changed their mind'),
    ('damaged_in_transit', 'Damaged'),
    ('other', 'Other'),
]
OUTCOMES = ('refund_cash', 'refund_momo', 'exchange', 'store_credit')
OUTCOME_LABELS = {
    'refund_cash': 'Cash back',
    'refund_momo': 'MoMo back',
    'exchange': 'Swap item',
    'store_credit': 'Taken off their debt',
}


def _already_returned(sale_item):
    return (Return.objects
            .filter(sale_item=sale_item, status__in=['pending', 'approved', 'resolved'])
            .aggregate(t=Sum('quantity'))['t'] or 0)


@transaction.atomic
def complete_return(ret, user, request=None):
    """Finish a return: stock, customer debt, activity log. Money is recorded on the return itself."""
    from inventory.utils import record_movement

    if ret.return_to_stock:
        record_movement(
            product=ret.product,
            movement_type='return',
            quantity=ret.quantity,
            user=user,
            reference_type='return',
            reference_id=ret.pk,
            reference_label=ret.return_number,
            serial_number=ret.serial_number or '',
            note="Return %s" % ret.return_number,
        )

    notes = ''
    if ret.resolution == 'store_credit' and ret.customer:
        ret.customer.reduce_credit(ret.refund_amount)
        notes = "GHS %s taken off the customer's debt." % ret.refund_amount

    ret.status = 'resolved'
    ret.approved_by = user
    ret.approved_at = timezone.now()
    if notes:
        ret.resolution_notes = notes
    ret.save()

    log_return(
        user,
        "Completed return %s: %s - GHS %s" % (
            ret.return_number, OUTCOME_LABELS.get(ret.resolution, ret.resolution), ret.refund_amount),
        obj=ret,
        request=request,
    )


@attendant_required
def find_sale_ajax(request):
    from sales.models import Sale
    q = (request.GET.get('q') or '').strip()
    found = []
    if q:
        for s in Sale.objects.filter(receipt_number__iendswith=q).order_by('-created_at')[:8]:
            found.append({
                'id': s.pk,
                'receipt': s.receipt_number,
                'date': s.created_at.strftime('%d %b %Y %H:%M'),
                'customer': s.customer_name or 'Walk-in',
                'total': str(s.total),
            })
    return JsonResponse({'sales': found})


@attendant_required
def sale_detail_ajax(request):
    from sales.models import Sale
    sale = get_object_or_404(Sale, pk=request.GET.get('sale_id'))
    items = []
    for it in sale.items.select_related('product'):
        left = it.quantity - _already_returned(it)
        unit_net = (it.subtotal / it.quantity) if it.quantity else it.unit_price
        items.append({
            'id': it.pk,
            'name': it.product_name,
            'serial': it.serial_number or '',
            'qty_sold': it.quantity,
            'qty_left': max(left, 0),
            'unit_net': str(Decimal(unit_net).quantize(Decimal('0.01'))),
        })
    cust = sale.customer
    return JsonResponse({
        'sale': {
            'id': sale.pk,
            'receipt': sale.receipt_number,
            'date': sale.created_at.strftime('%d %b %Y %H:%M'),
            'customer': sale.customer_name or 'Walk-in',
            'customer_owes': str(cust.credit_balance) if cust else '0',
            'has_customer': bool(cust),
        },
        'items': items,
    })


def _fail(request, text):
    messages.error(request, text)
    return redirect('returns:return_create')


@attendant_required
def return_new(request):
    if request.method != 'POST':
        return render(request, 'returns/return_form.html', {'reasons': REASONS})

    from sales.models import SaleItem
    try:
        item = SaleItem.objects.select_related('sale', 'product').get(pk=int(request.POST.get('sale_item_id', '')))
        qty = int(request.POST.get('quantity', ''))
    except Exception:
        return _fail(request, 'Please find the receipt and tap the item first.')

    reason = request.POST.get('reason', '')
    outcome = request.POST.get('outcome', '')
    if reason not in dict(REASONS) or outcome not in OUTCOMES:
        return _fail(request, 'Please choose why it came back and what happens.')

    left = item.quantity - _already_returned(item)
    if qty < 1 or qty > left:
        return _fail(request, 'Only %s of this item can still be returned.' % max(left, 0))

    sale = item.sale
    customer = sale.customer
    unit_net = (item.subtotal / item.quantity).quantize(Decimal('0.01'))
    refund = Decimal('0.00') if outcome == 'exchange' else (unit_net * qty).quantize(Decimal('0.01'))

    if outcome == 'store_credit':
        if not customer or customer.credit_balance <= 0:
            return _fail(request, 'This customer does not owe anything. Choose cash or MoMo back.')
        if refund > customer.credit_balance:
            return _fail(request, 'The customer owes only GHS %s, which is less than the refund. Choose cash back.'
                         % customer.credit_balance)

    if reason in ('customer_change_mind', 'wrong_item', 'other'):
        condition = 'working'
    elif reason == 'damaged_in_transit':
        condition = 'damaged'
    else:
        condition = 'faulty'

    ret = Return(
        sale=sale, sale_item=item, customer=customer, product=item.product,
        quantity=qty, serial_number=item.serial_number or '',
        reason=reason, reason_detail=(request.POST.get('note') or '').strip(),
        condition=condition, status='pending', resolution=outcome,
        original_price=unit_net, refund_amount=refund, restocking_fee=Decimal('0.00'),
        return_to_stock=(request.POST.get('put_back') == '1'), mark_as_damaged=False,
        processed_by=request.user,
    )
    ret.save()

    if request.user.is_owner:
        complete_return(ret, request.user, request)
        messages.success(request, 'Return %s done. %s: GHS %s.' % (
            ret.return_number, OUTCOME_LABELS[outcome], refund))
    else:
        log_return(request.user, 'Logged return %s (waiting for the owner)' % ret.return_number,
                   obj=ret, request=request)
        messages.success(request, 'Return %s saved. The owner must approve it before money or stock changes.'
                         % ret.return_number)
    return redirect('returns:return_detail', pk=ret.pk)


@owner_required
def return_approve_complete(request, pk):
    if request.method != 'POST':
        return redirect('returns:return_detail', pk=pk)
    ret = get_object_or_404(Return, pk=pk, status='pending')
    complete_return(ret, request.user, request)
    messages.success(request, 'Return %s approved and done.' % ret.return_number)
    return redirect('returns:return_detail', pk=pk)
