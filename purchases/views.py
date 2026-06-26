from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db import transaction
from django.utils import timezone

from accounts.decorators import owner_required, attendant_required
from audit.utils import log_purchase
from .models import Supplier, PurchaseOrder, PurchaseOrderItem, GoodsReceivedNote
from .forms import (
    SupplierForm, PurchaseOrderForm, PurchaseOrderItemFormSet,
    GRNForm, GRNItemForm, PaymentUpdateForm
)
from .utils import get_purchase_summary, receive_grn


# ─── Supplier Views ───────────────────────────────────────────────────────────

@owner_required
def supplier_list(request):
    suppliers = Supplier.objects.all()
    query = request.GET.get('q', '').strip()
    if query:
        suppliers = suppliers.filter(name__icontains=query)
    show_inactive = request.GET.get('inactive') == '1'
    if not show_inactive:
        suppliers = suppliers.filter(is_active=True)
    suppliers = suppliers.order_by('name')
    paginator = Paginator(suppliers, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'purchases/supplier_list.html', {
        'page_obj': page,
        'query': query,
        'show_inactive': show_inactive,
    })


@owner_required
def supplier_create(request):
    form = SupplierForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        supplier = form.save()
        log_purchase(
            request.user,
            f"Added supplier: {supplier.name}",
            obj=supplier,
            request=request
        )
        messages.success(request, f"Supplier '{supplier.name}' added.")
        return redirect('purchases:supplier_list')
    return render(request, 'purchases/supplier_form.html', {'form': form, 'title': 'Add Supplier'})


@owner_required
def supplier_edit(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    form = SupplierForm(request.POST or None, instance=supplier)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_purchase(
            request.user,
            f"Updated supplier: {supplier.name}",
            obj=supplier,
            request=request
        )
        messages.success(request, "Supplier updated.")
        return redirect('purchases:supplier_list')
    return render(request, 'purchases/supplier_form.html', {'form': form, 'title': 'Edit Supplier', 'supplier': supplier})


@owner_required
def supplier_detail(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    orders = supplier.purchaseorder_set.select_related('created_by').order_by('-created_at')[:20]
    return render(request, 'purchases/supplier_detail.html', {
        'supplier': supplier,
        'recent_orders': orders,
    })


# ─── Purchase Order Views ─────────────────────────────────────────────────────

@owner_required
def po_list(request):
    pos = PurchaseOrder.objects.select_related('supplier', 'created_by')
    status = request.GET.get('status', '')
    supplier_id = request.GET.get('supplier', '')
    query = request.GET.get('q', '').strip()
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if status:
        pos = pos.filter(status=status)
    if supplier_id:
        pos = pos.filter(supplier_id=supplier_id)
    if query:
        pos = pos.filter(po_number__icontains=query)
    if date_from:
        pos = pos.filter(order_date__gte=date_from)
    if date_to:
        pos = pos.filter(order_date__lte=date_to)

    pos = pos.order_by('-created_at')
    paginator = Paginator(pos, 20)
    page = paginator.get_page(request.GET.get('page'))

    summary = get_purchase_summary()
    suppliers = Supplier.objects.filter(is_active=True).order_by('name')

    return render(request, 'purchases/po_list.html', {
        'page_obj': page,
        'summary': summary,
        'suppliers': suppliers,
        'selected_status': status,
        'selected_supplier': supplier_id,
        'query': query,
        'date_from': date_from,
        'date_to': date_to,
        'status_choices': PurchaseOrder.STATUS_CHOICES,
    })


@owner_required
def po_create(request):
    form = PurchaseOrderForm(request.POST or None)
    formset = PurchaseOrderItemFormSet(request.POST or None)

    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        with transaction.atomic():
            po = form.save(commit=False)
            po.created_by = request.user
            po.save()
            formset.instance = po
            formset.save()
            po._recalculate_totals()
            po.save()

        log_purchase(
            request.user,
            f"Created PO {po.po_number} for {po.supplier.name} — GH₵{po.grand_total}",
            obj=po,
            request=request
        )
        messages.success(request, f"Purchase Order {po.po_number} created.")
        return redirect('purchases:po_detail', pk=po.pk)

    return render(request, 'purchases/po_form.html', {
        'form': form,
        'formset': formset,
        'title': 'New Purchase Order',
    })


@owner_required
def po_edit(request, pk):
    po = get_object_or_404(PurchaseOrder, pk=pk)
    if not po.can_be_edited():
        messages.error(request, "Only draft orders can be edited.")
        return redirect('purchases:po_detail', pk=po.pk)

    form = PurchaseOrderForm(request.POST or None, instance=po)
    formset = PurchaseOrderItemFormSet(request.POST or None, instance=po)

    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        with transaction.atomic():
            form.save()
            formset.save()
            po._recalculate_totals()
            po.save()

        messages.success(request, f"PO {po.po_number} updated.")
        return redirect('purchases:po_detail', pk=po.pk)

    return render(request, 'purchases/po_form.html', {
        'form': form,
        'formset': formset,
        'title': f'Edit {po.po_number}',
        'po': po,
    })


@owner_required
def po_detail(request, pk):
    po = get_object_or_404(
        PurchaseOrder.objects.select_related('supplier', 'created_by', 'approved_by'),
        pk=pk
    )
    items = po.items.select_related('product__category').all()
    grns = po.grns.select_related('received_by').prefetch_related('grn_items__po_item__product')
    return render(request, 'purchases/po_detail.html', {
        'po': po,
        'items': items,
        'grns': grns,
    })


@owner_required
def po_mark_ordered(request, pk):
    if request.method != 'POST':
        return redirect('purchases:po_detail', pk=pk)
    po = get_object_or_404(PurchaseOrder, pk=pk)
    try:
        po.mark_ordered(request.user)
        log_purchase(
            request.user,
            f"Marked PO {po.po_number} as Ordered",
            obj=po,
            request=request
        )
        messages.success(request, f"PO {po.po_number} marked as Ordered.")
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('purchases:po_detail', pk=pk)


@owner_required
def po_cancel(request, pk):
    if request.method != 'POST':
        return redirect('purchases:po_detail', pk=pk)
    po = get_object_or_404(PurchaseOrder, pk=pk)
    try:
        po.cancel(request.user)
        log_purchase(
            request.user,
            f"Cancelled PO {po.po_number}",
            obj=po,
            request=request,
            level='warning'
        )
        messages.warning(request, f"PO {po.po_number} has been cancelled.")
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('purchases:po_list')


# ─── GRN (Receive Stock) Views ────────────────────────────────────────────────

@owner_required
def grn_create(request, po_pk):
    po = get_object_or_404(PurchaseOrder, pk=po_pk, status__in=['ordered', 'partial'])
    pending_items = po.items.filter(
        quantity_received__lt=models.F('quantity_ordered')
    ).select_related('product')

    # Build a GRNItemForm for each pending item
    grn_form = GRNForm(request.POST or None, initial={'received_date': timezone.now().date()})
    item_forms = []
    for item in pending_items:
        prefix = f"item_{item.pk}"
        item_forms.append({
            'po_item': item,
            'form': GRNItemForm(
                request.POST or None,
                prefix=prefix,
                initial={
                    'po_item_id': item.pk,
                    'quantity_received': item.quantity_pending,
                    'condition': 'new',
                }
            )
        })

    if request.method == 'POST' and grn_form.is_valid():
        all_item_forms_valid = all(
            entry['form'].is_valid() for entry in item_forms
        )
        if all_item_forms_valid:
            with transaction.atomic():
                grn = grn_form.save(commit=False)
                grn.purchase_order = po
                grn.received_by = request.user
                grn.save()

                grn_item_data = []
                for entry in item_forms:
                    f = entry['form']
                    grn_item_data.append({
                        'po_item_id': f.cleaned_data['po_item_id'],
                        'quantity_received': f.cleaned_data['quantity_received'],
                        'condition': f.cleaned_data['condition'],
                        'notes': f.cleaned_data.get('notes', ''),
                    })

                receive_grn(grn, grn_item_data, request.user)

            log_purchase(
                request.user,
                f"Received stock via GRN {grn.grn_number} for PO {po.po_number}",
                obj=grn,
                request=request
            )
            messages.success(request, f"GRN {grn.grn_number} recorded. Stock updated.")
            return redirect('purchases:po_detail', pk=po.pk)

    return render(request, 'purchases/grn_form.html', {
        'po': po,
        'grn_form': grn_form,
        'item_forms': item_forms,
    })


@owner_required
def payment_update(request, pk):
    po = get_object_or_404(PurchaseOrder, pk=pk)
    form = PaymentUpdateForm(request.POST or None, instance=po)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_purchase(
            request.user,
            f"Recorded payment GH₵{po.amount_paid} for PO {po.po_number}",
            obj=po,
            request=request
        )
        messages.success(request, f"Payment updated. Amount due: GH₵{po.amount_due}")
        return redirect('purchases:po_detail', pk=pk)
    return render(request, 'purchases/payment_form.html', {'form': form, 'po': po})


# ─── AJAX ─────────────────────────────────────────────────────────────────────

@login_required
def supplier_search_ajax(request):
    """AJAX supplier search for PO form autocomplete."""
    from accounts.decorators import ajax_required
    q = request.GET.get('q', '').strip()
    results = []
    if len(q) >= 2:
        suppliers = Supplier.objects.filter(
            name__icontains=q, is_active=True
        ).values('id', 'name', 'phone', 'contact_person')[:10]
        results = list(suppliers)
    return JsonResponse({'results': results})


# Import models.F used in grn_create
from django.db import models