from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction

from accounts.decorators import owner_required, attendant_required
from audit.utils import log_return
from .models import Return
from .forms import ReturnCreateForm, ReturnResolveForm, ReturnRejectForm, ReturnFilterForm
from .utils import process_return_resolution, get_return_summary


@attendant_required
def return_list(request):
    returns = Return.objects.select_related('product', 'customer', 'processed_by')

    # Attendants only see their own returns
    if not request.user.is_owner:
        returns = returns.filter(processed_by=request.user)

    form = ReturnFilterForm(request.GET or None)
    if form.is_valid():
        q = form.cleaned_data.get('q')
        status = form.cleaned_data.get('status')
        reason = form.cleaned_data.get('reason')
        date_from = form.cleaned_data.get('date_from')
        date_to = form.cleaned_data.get('date_to')

        if q:
            returns = returns.filter(
                return_number__icontains=q
            ) | returns.filter(
                product__name__icontains=q
            )
        if status:
            returns = returns.filter(status=status)
        if reason:
            returns = returns.filter(reason=reason)
        if date_from:
            returns = returns.filter(return_date__gte=date_from)
        if date_to:
            returns = returns.filter(return_date__lte=date_to)

    returns = returns.order_by('-created_at')
    paginator = Paginator(returns, 20)
    page = paginator.get_page(request.GET.get('page'))

    summary = get_return_summary() if request.user.is_owner else {}

    return render(request, 'returns/return_list.html', {
        'page_obj': page,
        'filter_form': form,
        'summary': summary,
    })


@attendant_required
def return_create(request):
    form = ReturnCreateForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        ret = form.save(commit=False)
        ret.processed_by = request.user
        ret.save()
        log_return(
            request.user,
            f"Logged return {ret.return_number} for {ret.product.name}",
            obj=ret,
            request=request
        )
        messages.success(request, f"Return {ret.return_number} logged. Awaiting owner approval.")
        return redirect('returns:return_detail', pk=ret.pk)
    return render(request, 'returns/return_form.html', {'form': form, 'title': 'Log New Return'})


@attendant_required
def return_detail(request, pk):
    ret = get_object_or_404(
        Return.objects.select_related(
            'sale', 'sale_item', 'customer', 'product',
            'processed_by', 'approved_by'
        ),
        pk=pk
    )
    # Attendants can only view their own returns
    if not request.user.is_owner and ret.processed_by != request.user:
        messages.error(request, "You don't have permission to view this return.")
        return redirect('returns:return_list')

    resolve_form = ReturnResolveForm(instance=ret) if request.user.is_owner else None
    reject_form = ReturnRejectForm() if request.user.is_owner else None

    return render(request, 'returns/return_detail.html', {
        'return': ret,
        'resolve_form': resolve_form,
        'reject_form': reject_form,
    })


@owner_required
def return_approve(request, pk):
    if request.method != 'POST':
        return redirect('returns:return_detail', pk=pk)
    ret = get_object_or_404(Return, pk=pk, status='pending')
    ret.approve(request.user)
    log_return(
        request.user,
        f"Approved return {ret.return_number}",
        obj=ret,
        request=request
    )
    messages.success(request, f"Return {ret.return_number} approved.")
    return redirect('returns:return_detail', pk=pk)


@owner_required
def return_reject(request, pk):
    if request.method != 'POST':
        return redirect('returns:return_detail', pk=pk)
    ret = get_object_or_404(Return, pk=pk, status__in=['pending', 'approved'])
    form = ReturnRejectForm(request.POST)
    if form.is_valid():
        notes = form.cleaned_data.get('rejection_notes', '')
        ret.reject(request.user, notes)
        log_return(
            request.user,
            f"Rejected return {ret.return_number}",
            obj=ret,
            request=request,
            level='warning'
        )
        messages.warning(request, f"Return {ret.return_number} rejected.")
    return redirect('returns:return_detail', pk=pk)


@owner_required
def return_resolve(request, pk):
    if request.method != 'POST':
        return redirect('returns:return_detail', pk=pk)
    ret = get_object_or_404(Return, pk=pk, status='approved')
    form = ReturnResolveForm(request.POST, instance=ret)
    if form.is_valid():
        with transaction.atomic():
            resolved_return = form.save(commit=False)
            resolved_return.status = 'resolved'
            resolved_return.save()
            process_return_resolution(resolved_return, request.user)
        messages.success(
            request,
            f"Return {ret.return_number} resolved: {ret.get_resolution_display()}. "
            f"Net refund: GH₵{ret.net_refund}"
        )
        return redirect('returns:return_detail', pk=pk)

    # If form invalid, re-render detail page with errors
    messages.error(request, "Please fix the errors below.")
    return redirect('returns:return_detail', pk=pk)


@attendant_required
def return_sale_items_ajax(request):
    """AJAX: returns SaleItems for a given sale (for the create form dropdown)."""
    from django.http import JsonResponse
    from sales.models import SaleItem
    sale_id = request.GET.get('sale_id')
    items = []
    if sale_id:
        sale_items = SaleItem.objects.filter(
            sale_id=sale_id
        ).select_related('product').values(
            'id', 'product__name', 'product__id', 'quantity', 'unit_price', 'serial_number'
        )
        items = list(sale_items)
    return JsonResponse({'items': items})