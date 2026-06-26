from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST, require_GET

from accounts.decorators import owner_required, attendant_required, ajax_required
from audit.models import AuditLog
from audit.utils import log_action
from .forms import DiscountForm, ApplyDiscountForm
from .models import Discount, DiscountUsage
from .utils import get_discount_by_code, validate_discount, get_discount_summary


# ── List ──────────────────────────────────────────────────────────────────────

@owner_required
def discount_list(request):
    discounts = Discount.objects.all()

    q       = request.GET.get('q', '').strip()
    status  = request.GET.get('status', '').strip()
    dtype   = request.GET.get('type', '').strip()

    if q:
        discounts = discounts.filter(name__icontains=q) | \
                    discounts.filter(code__icontains=q)

    if status == 'active':
        discounts = discounts.filter(is_active=True)
    elif status == 'inactive':
        discounts = discounts.filter(is_active=False)

    if dtype:
        discounts = discounts.filter(discount_type=dtype)

    paginator = Paginator(discounts, 20)
    page_obj  = paginator.get_page(request.GET.get('page'))

    summary = get_discount_summary()

    context = {
        'page_obj': page_obj,
        'summary':  summary,
        'types':    Discount.TYPE_CHOICES,
        'filters':  {'q': q, 'status': status, 'type': dtype},
    }
    return render(request, 'discounts/discount_list.html', context)


# ── Create ────────────────────────────────────────────────────────────────────

@owner_required
def discount_create(request):
    form = DiscountForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        discount = form.save(commit=False)
        discount.created_by = request.user
        # Normalise code to uppercase
        if discount.code:
            discount.code = discount.code.upper()
        discount.save()
        form.save_m2m()  # Save ManyToMany (products, categories)

        log_action(
            user=request.user,
            category=AuditLog.CATEGORY_DISCOUNT,
            action=f'Created discount: {discount.name}',
            object_type='Discount',
            object_id=discount.id,
            object_repr=str(discount),
            request=request,
        )
        messages.success(request, f'Discount "{discount.name}" created.')
        return redirect('discounts:list')

    return render(request, 'discounts/discount_form.html', {'form': form, 'action': 'Create'})


# ── Edit ──────────────────────────────────────────────────────────────────────

@owner_required
def discount_edit(request, pk):
    discount = get_object_or_404(Discount, pk=pk)
    form     = DiscountForm(request.POST or None, instance=discount)

    if request.method == 'POST' and form.is_valid():
        disc = form.save(commit=False)
        if disc.code:
            disc.code = disc.code.upper()
        disc.save()
        form.save_m2m()

        log_action(
            user=request.user,
            category=AuditLog.CATEGORY_DISCOUNT,
            action=f'Updated discount: {discount.name}',
            object_type='Discount',
            object_id=discount.id,
            object_repr=str(discount),
            request=request,
        )
        messages.success(request, f'Discount "{discount.name}" updated.')
        return redirect('discounts:list')

    return render(request, 'discounts/discount_form.html', {
        'form': form, 'discount': discount, 'action': 'Edit'
    })


# ── Toggle active ─────────────────────────────────────────────────────────────

@owner_required
@require_POST
def discount_toggle(request, pk):
    discount = get_object_or_404(Discount, pk=pk)
    discount.is_active = not discount.is_active
    discount.save(update_fields=['is_active', 'updated_at'])

    state = 'activated' if discount.is_active else 'deactivated'
    log_action(
        user=request.user,
        category=AuditLog.CATEGORY_DISCOUNT,
        action=f'Discount {state}: {discount.name}',
        object_type='Discount',
        object_id=discount.id,
        object_repr=str(discount),
        level=AuditLog.LEVEL_WARNING,
        request=request,
    )
    messages.success(request, f'"{discount.name}" has been {state}.')
    return redirect('discounts:list')


# ── Delete ────────────────────────────────────────────────────────────────────

@owner_required
@require_POST
def discount_delete(request, pk):
    discount = get_object_or_404(Discount, pk=pk)

    if discount.usage_records.exists():
        messages.error(
            request,
            f'Cannot delete "{discount.name}" — it has been used in sales. '
            'Deactivate it instead.'
        )
        return redirect('discounts:list')

    name = str(discount)
    discount.delete()

    log_action(
        user=request.user,
        category=AuditLog.CATEGORY_DISCOUNT,
        action=f'Deleted discount: {name}',
        level=AuditLog.LEVEL_WARNING,
        request=request,
    )
    messages.success(request, f'Discount "{name}" deleted.')
    return redirect('discounts:list')


# ── Usage history ─────────────────────────────────────────────────────────────

@owner_required
def discount_usage(request, pk):
    discount = get_object_or_404(Discount, pk=pk)
    usages   = discount.usage_records.select_related('customer', 'sale', 'applied_by')

    paginator = Paginator(usages, 20)
    page_obj  = paginator.get_page(request.GET.get('page'))

    return render(request, 'discounts/discount_usage.html', {
        'discount': discount,
        'page_obj': page_obj,
    })


# ── AJAX: validate promo code from POS ───────────────────────────────────────

@ajax_required
@attendant_required
@require_GET
def validate_code_ajax(request):
    """
    The POS calls this when a cashier enters a promo code.
    Returns whether the code is valid and how much it will save.

    Query params:
        code       — the promo code entered
        cart_total — the current cart total as a number
        customer_id — optional customer PK
    """
    code       = request.GET.get('code', '').strip().upper()
    cart_total_str = request.GET.get('cart_total', '0')
    customer_id    = request.GET.get('customer_id')

    if not code:
        return JsonResponse({'valid': False, 'error': 'No code provided.'})

    try:
        from decimal import Decimal
        cart_total = Decimal(cart_total_str)
    except Exception:
        return JsonResponse({'valid': False, 'error': 'Invalid cart total.'})

    discount = get_discount_by_code(code)
    if not discount:
        return JsonResponse({'valid': False, 'error': 'Invalid or expired promo code.'})

    customer = None
    if customer_id:
        try:
            from customers.models import Customer
            customer = Customer.objects.get(pk=customer_id, is_active=True)
        except Customer.DoesNotExist:
            pass

    is_valid, error, amount = validate_discount(discount, cart_total, customer)

    if not is_valid:
        return JsonResponse({'valid': False, 'error': error})

    return JsonResponse({
        'valid':           True,
        'discount_id':     discount.id,
        'discount_name':   discount.name,
        'discount_type':   discount.discount_type,
        'amount_saved':    str(amount),
        'requires_pin':    discount.requires_pin,
    })