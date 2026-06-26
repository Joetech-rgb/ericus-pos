from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import F, Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from accounts.decorators import owner_required, pin_required
from products.models import Product, ProductUnit, Category
from audit.utils import log_inventory, log_system

from .models import StockLevel, StockMovement, DemoUnit, StockAudit, StockAuditItem
from .forms import (
    StockAdjustmentForm, DemoUnitForm, ReturnDemoForm,
    StockAuditForm, StockAuditItemForm, StockSearchForm,
)
from .utils import (
    record_movement, get_low_stock_list, get_out_of_stock_list,
    get_stock_summary, get_active_demo_units, create_demo_unit,
    return_demo_to_stock, generate_audit_reference, complete_stock_audit,
    get_recent_movements,
)


# ─── Stock Dashboard ──────────────────────────────────────────────────────────

@login_required
def stock_dashboard(request):
    form = StockSearchForm(request.GET)
    categories = Category.objects.all()

    qs = (
        StockLevel.objects
        .select_related('product', 'product__category')
        .order_by('product__name')
    )

    search = request.GET.get('search', '').strip()
    category_id = request.GET.get('category', '')
    status_filter = request.GET.get('status', '')

    if search:
        qs = qs.filter(
            Q(product__name__icontains=search) |
            Q(product__brand__icontains=search) |
            Q(product__sku__icontains=search) |
            Q(product__barcode__icontains=search)
        )
    if category_id:
        qs = qs.filter(product__category_id=category_id)
    if status_filter == 'out':
        qs = qs.filter(quantity=0)
    elif status_filter == 'low':
        qs = qs.filter(quantity__gt=0, quantity__lte=F('product__reorder_point'))
    elif status_filter == 'ok':
        qs = qs.filter(quantity__gt=F('product__reorder_point'))

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    summary = get_stock_summary()
    recent_movements = get_recent_movements(10)

    return render(request, 'inventory/stock_dashboard.html', {
        'page_obj': page_obj,
        'categories': categories,
        'summary': summary,
        'recent_movements': recent_movements,
        'form': form,
        'search': search,
        'selected_category': category_id,
        'selected_status': status_filter,
    })


# ─── Product Stock Detail ─────────────────────────────────────────────────────

@login_required
def stock_detail(request, product_pk):
    """Full movement history for one product."""
    product = get_object_or_404(Product, pk=product_pk)
    stock_level, _ = StockLevel.objects.get_or_create(
        product=product,
        defaults={'quantity': 0},
    )
    movements = (
        StockMovement.objects
        .filter(product=product)
        .select_related('created_by')
        .order_by('-created_at')
    )
    units = ProductUnit.objects.filter(product=product).order_by('-received_at')  # ✅ FIXED
    demo_units = DemoUnit.objects.filter(product=product, is_active=True)

    paginator = Paginator(movements, 30)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'inventory/stock_detail.html', {
        'product': product,
        'stock_level': stock_level,
        'page_obj': page_obj,
        'units': units,
        'demo_units': demo_units,
    })


# ─── Stock Adjustment (PIN required) ─────────────────────────────────────────

@login_required
@pin_required('Stock Adjustment')
def stock_adjustment(request, product_pk):
    product = get_object_or_404(Product, pk=product_pk)
    stock_level, _ = StockLevel.objects.get_or_create(
        product=product,
        defaults={'quantity': 0},
    )

    if request.method == 'POST':
        form = StockAdjustmentForm(request.POST)
        form.data = form.data.copy()
        form.data['product_id'] = product.pk

        if form.is_valid():
            try:
                movement = record_movement(
                    product=product,
                    movement_type=form.movement_type(),
                    quantity=form.cleaned_data['quantity'],
                    user=request.user,
                    note=form.cleaned_data['note'],
                    serial_number=form.cleaned_data.get('serial_number', ''),
                )
                direction_word = "added" if form.cleaned_data['direction'] == 'in' else "removed"
                messages.success(
                    request,
                    f"Stock adjusted — {form.cleaned_data['quantity']} unit(s) {direction_word}. "
                    f"New total: {movement.quantity_after}"
                )
                log_inventory(
                    request.user,
                    f"Manual stock adjustment on {product.name}: "
                    f"{'+' if form.cleaned_data['direction'] == 'in' else '-'}"
                    f"{form.cleaned_data['quantity']} units — {form.cleaned_data['note']}",
                    request=request,
                )
                return redirect('inventory:stock_detail', product_pk=product.pk)
            except ValueError as e:
                messages.error(request, str(e))
    else:
        form = StockAdjustmentForm(initial={'product_id': product.pk})

    return render(request, 'inventory/stock_adjustment.html', {
        'product': product,
        'stock_level': stock_level,
        'form': form,
    })


# ─── Demo Unit Management ─────────────────────────────────────────────────────

@login_required
def demo_unit_list(request):
    demo_units = get_active_demo_units()
    return render(request, 'inventory/demo_units.html', {
        'demo_units': demo_units,
    })


@login_required
@owner_required
def convert_to_demo(request, unit_pk):
    unit = get_object_or_404(ProductUnit, pk=unit_pk)

    if unit.status != 'in_stock':
        messages.error(request, "Only in-stock units can be converted to demo.")
        return redirect('inventory:stock_detail', product_pk=unit.product.pk)

    if request.method == 'POST':
        form = DemoUnitForm(request.POST)
        if form.is_valid():
            try:
                demo = create_demo_unit(unit, request.user)
                if form.cleaned_data.get('condition_notes'):
                    demo.condition_notes = form.cleaned_data['condition_notes']
                    demo.save()
                messages.success(
                    request,
                    f"{unit.product.name} (S/N: {unit.serial_number}) moved to floor display."
                )
                log_inventory(
                    request.user,
                    f"Unit {unit.serial_number} of {unit.product.name} converted to demo unit",
                    request=request,
                )
            except Exception as e:
                messages.error(request, str(e))
            return redirect('inventory:stock_detail', product_pk=unit.product.pk)
    else:
        form = DemoUnitForm(initial={'product_unit_id': unit.pk})

    return render(request, 'inventory/convert_to_demo.html', {
        'unit': unit,
        'form': form,
    })


@login_required
@owner_required
@require_POST
def return_demo(request, demo_pk):
    demo = get_object_or_404(DemoUnit, pk=demo_pk, is_active=True)
    form = ReturnDemoForm(request.POST)
    if form.is_valid():
        try:
            return_demo_to_stock(demo, request.user, note=form.cleaned_data.get('note', ''))
            messages.success(request, f"{demo.product.name} demo unit returned to sellable stock.")
            log_inventory(
                request.user,
                f"Demo unit of {demo.product.name} returned to sellable stock",
                request=request,
            )
        except Exception as e:
            messages.error(request, str(e))
    return redirect('inventory:demo_units')


# ─── Stock Audit ─────────────────────────────────────────────────────────────

@login_required
@owner_required
def audit_list(request):
    audits = StockAudit.objects.select_related('conducted_by').order_by('-started_at')
    return render(request, 'inventory/audit_list.html', {'audits': audits})


@login_required
@owner_required
def audit_create(request):
    if request.method == 'POST':
        form = StockAuditForm(request.POST)
        if form.is_valid():
            audit = form.save(commit=False)
            audit.reference = generate_audit_reference()
            audit.conducted_by = request.user
            audit.save()

            stock_levels = StockLevel.objects.select_related('product').all()
            items = [
                StockAuditItem(
                    audit=audit,
                    product=sl.product,
                    system_count=sl.quantity,
                    physical_count=sl.quantity,
                )
                for sl in stock_levels
            ]
            StockAuditItem.objects.bulk_create(items)

            messages.success(request, f"Stock audit {audit.reference} started.")
            log_system(
                request.user,
                f"Stock audit {audit.reference} started",
                request=request,
            )
            return redirect('inventory:audit_detail', pk=audit.pk)
    else:
        form = StockAuditForm()
    return render(request, 'inventory/audit_create.html', {'form': form})


@login_required
@owner_required
def audit_detail(request, pk):
    audit = get_object_or_404(StockAudit, pk=pk)
    items = audit.items.select_related('product', 'product__category').order_by('product__name')
    return render(request, 'inventory/audit_detail.html', {
        'audit': audit,
        'items': items,
    })


@login_required
@owner_required
@require_POST
def audit_update_item(request, pk, item_pk):
    audit = get_object_or_404(StockAudit, pk=pk, status='open')
    item = get_object_or_404(StockAuditItem, pk=item_pk, audit=audit)
    form = StockAuditItemForm(request.POST, instance=item)
    if form.is_valid():
        form.save()
        return JsonResponse({
            'ok': True,
            'discrepancy': item.discrepancy,
            'has_discrepancy': item.has_discrepancy,
        })
    return JsonResponse({'ok': False, 'errors': form.errors}, status=400)


@login_required
@owner_required
@require_POST
def audit_complete(request, pk):
    audit = get_object_or_404(StockAudit, pk=pk, status='open')
    try:
        complete_stock_audit(audit, request.user)
        messages.success(
            request,
            f"Audit {audit.reference} completed. "
            f"{audit.discrepancy_count} product(s) had discrepancies — stock corrected."
        )
        log_system(
            request.user,
            f"Stock audit {audit.reference} completed — {audit.discrepancy_count} discrepancies corrected",
            request=request,
        )
    except Exception as e:
        messages.error(request, str(e))
    return redirect('inventory:audit_detail', pk=audit.pk)


@login_required
@owner_required
@require_POST
def audit_cancel(request, pk):
    audit = get_object_or_404(StockAudit, pk=pk, status='open')
    audit.status = 'cancelled'
    audit.save()
    messages.warning(request, f"Audit {audit.reference} cancelled.")
    return redirect('inventory:audit_list')


# ─── Movement Log ─────────────────────────────────────────────────────────────

@login_required
@owner_required
def movement_log(request):
    qs = (
        StockMovement.objects
        .select_related('product', 'product__category', 'created_by')
        .order_by('-created_at')
    )

    search = request.GET.get('search', '').strip()
    movement_type = request.GET.get('type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if search:
        qs = qs.filter(
            Q(product__name__icontains=search) |
            Q(serial_number__icontains=search) |
            Q(note__icontains=search)
        )
    if movement_type:
        qs = qs.filter(movement_type=movement_type)
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    paginator = Paginator(qs, 30)
    page_obj = paginator.get_page(request.GET.get('page'))

    movement_types = StockMovement.MOVEMENT_TYPES

    return render(request, 'inventory/movement_log.html', {
        'page_obj': page_obj,
        'movement_types': movement_types,
        'search': search,
        'selected_type': movement_type,
        'date_from': date_from,
        'date_to': date_to,
    })