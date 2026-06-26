from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q

from .models import WholesaleOrder, WholesaleOrderItem
from .forms import WholesaleOrderForm, WholesaleOrderItemFormSet, WholesalePaymentForm
from .utils import (
    get_wholesale_summary,
    get_recent_wholesale_orders,
    get_top_wholesale_customers,
    process_wholesale_delivery,
)


# ─── Dashboard ───────────────────────────────────────────────────────────────

@login_required
def wholesale_dashboard(request):
    summary = get_wholesale_summary()
    recent_orders = get_recent_wholesale_orders(limit=10)
    top_customers = get_top_wholesale_customers(limit=5)
    context = {
        'summary': summary,
        'recent_orders': recent_orders,
        'top_customers': top_customers,
    }
    return render(request, 'wholesale/dashboard.html', context)


# ─── Order List ───────────────────────────────────────────────────────────────

@login_required
def order_list(request):
    qs = WholesaleOrder.objects.select_related('customer', 'created_by')

    # Filters
    status = request.GET.get('status', '')
    payment_status = request.GET.get('payment_status', '')
    search = request.GET.get('q', '')

    if status:
        qs = qs.filter(status=status)
    if payment_status:
        qs = qs.filter(payment_status=payment_status)
    if search:
        qs = qs.filter(
            Q(order_number__icontains=search) |
            Q(customer__name__icontains=search)
        )

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'status_choices': WholesaleOrder.STATUS_CHOICES,
        'payment_status_choices': WholesaleOrder.PAYMENT_STATUS_CHOICES,
        'current_status': status,
        'current_payment_status': payment_status,
        'search': search,
    }
    return render(request, 'wholesale/order_list.html', context)


# ─── Order Detail ─────────────────────────────────────────────────────────────

@login_required
def order_detail(request, pk):
    order = get_object_or_404(
        WholesaleOrder.objects.select_related('customer', 'created_by').prefetch_related('items__product'),
        pk=pk
    )
    payment_form = WholesalePaymentForm(instance=order)
    context = {
        'order': order,
        'payment_form': payment_form,
    }
    return render(request, 'wholesale/order_detail.html', context)


# ─── Create Order ─────────────────────────────────────────────────────────────

@login_required
def order_create(request):
    if request.method == 'POST':
        form = WholesaleOrderForm(request.POST)
        formset = WholesaleOrderItemFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                order = form.save(commit=False)
                order.created_by = request.user
                order.save()
                formset.instance = order
                formset.save()
            messages.success(request, f"Order {order.order_number} created successfully.")
            return redirect('wholesale:order_detail', pk=order.pk)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = WholesaleOrderForm()
        formset = WholesaleOrderItemFormSet()

    context = {
        'form': form,
        'formset': formset,
        'title': 'Create Wholesale Order',
    }
    return render(request, 'wholesale/order_form.html', context)


# ─── Edit Order ───────────────────────────────────────────────────────────────

@login_required
def order_edit(request, pk):
    order = get_object_or_404(WholesaleOrder, pk=pk)
    if not order.can_be_edited():
        messages.error(request, f"Order {order.order_number} cannot be edited in its current status.")
        return redirect('wholesale:order_detail', pk=pk)

    if request.method == 'POST':
        form = WholesaleOrderForm(request.POST, instance=order)
        formset = WholesaleOrderItemFormSet(request.POST, instance=order)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                form.save()
                formset.save()
            messages.success(request, f"Order {order.order_number} updated successfully.")
            return redirect('wholesale:order_detail', pk=order.pk)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = WholesaleOrderForm(instance=order)
        formset = WholesaleOrderItemFormSet(instance=order)

    context = {
        'form': form,
        'formset': formset,
        'order': order,
        'title': f'Edit Order {order.order_number}',
    }
    return render(request, 'wholesale/order_form.html', context)


# ─── Confirm Order ────────────────────────────────────────────────────────────

@login_required
def order_confirm(request, pk):
    order = get_object_or_404(WholesaleOrder, pk=pk)
    if request.method == 'POST':
        try:
            order.confirm(user=request.user)
            messages.success(request, f"Order {order.order_number} has been confirmed.")
        except ValueError as e:
            messages.error(request, str(e))
    return redirect('wholesale:order_detail', pk=pk)


# ─── Mark as Packed ───────────────────────────────────────────────────────────

@login_required
def order_mark_packed(request, pk):
    order = get_object_or_404(WholesaleOrder, pk=pk)
    if request.method == 'POST':
        if order.status != 'confirmed':
            messages.error(request, "Only confirmed orders can be marked as packed.")
        else:
            order.status = 'packed'
            order.save()
            messages.success(request, f"Order {order.order_number} marked as packed.")
    return redirect('wholesale:order_detail', pk=pk)


# ─── Mark as Delivered ────────────────────────────────────────────────────────

@login_required
def order_deliver(request, pk):
    order = get_object_or_404(WholesaleOrder, pk=pk)
    if request.method == 'POST':
        if order.status != 'packed':
            messages.error(request, "Only packed orders can be marked as delivered.")
        else:
            try:
                process_wholesale_delivery(order, request.user)
                messages.success(request, f"Order {order.order_number} delivered and stock updated.")
            except Exception as e:
                messages.error(request, f"Delivery failed: {e}")
    return redirect('wholesale:order_detail', pk=pk)


# ─── Cancel Order ─────────────────────────────────────────────────────────────

@login_required
def order_cancel(request, pk):
    order = get_object_or_404(WholesaleOrder, pk=pk)
    if request.method == 'POST':
        try:
            order.cancel()
            messages.success(request, f"Order {order.order_number} has been cancelled.")
        except ValueError as e:
            messages.error(request, str(e))
    return redirect('wholesale:order_detail', pk=pk)


# ─── Record Payment ───────────────────────────────────────────────────────────

@login_required
def order_payment(request, pk):
    order = get_object_or_404(WholesaleOrder, pk=pk)
    if request.method == 'POST':
        form = WholesalePaymentForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f"Payment recorded. Amount due: GH₵{order.amount_due:.2f}"
            )
        else:
            messages.error(request, "Invalid payment data. Please check the form.")
    return redirect('wholesale:order_detail', pk=pk)


# ─── AJAX: Product Price Lookup ───────────────────────────────────────────────

@login_required
def product_price_ajax(request):
    """Return the wholesale price of a product for inline price population."""
    product_id = request.GET.get('product_id')
    if not product_id:
        return JsonResponse({'error': 'No product_id provided.'}, status=400)
    try:
        from products.models import Product
        product = Product.objects.get(pk=product_id, is_active=True)
        return JsonResponse({
            'price': str(product.wholesale_price or product.selling_price),
            'name': product.name,
        })
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found.'}, status=404)