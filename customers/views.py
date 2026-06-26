import json

from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST, require_GET

from accounts.decorators import owner_required, attendant_required, ajax_required
from audit.models import AuditLog
from audit.utils import log_customer
from .forms import CustomerForm, CreditPaymentForm
from .models import Customer, CreditPayment


# ── List ──────────────────────────────────────────────────────────────────────

@attendant_required
def customer_list(request):
    customers = Customer.objects.filter(is_active=True)

    q            = request.GET.get('q', '').strip()
    ctype        = request.GET.get('type', '').strip()
    has_balance  = request.GET.get('balance', '').strip()

    if q:
        customers = customers.filter(full_name__icontains=q) | \
                    customers.filter(phone__icontains=q) | \
                    customers.filter(company_name__icontains=q)

    if ctype in [Customer.TYPE_RETAIL, Customer.TYPE_WHOLESALE]:
        customers = customers.filter(customer_type=ctype)

    if has_balance == '1':
        customers = customers.filter(credit_balance__gt=0)

    paginator = Paginator(customers, 25)
    page_obj  = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'filters': {'q': q, 'type': ctype, 'balance': has_balance},
        'total_with_balance': Customer.objects.filter(credit_balance__gt=0).count(),
    }
    return render(request, 'customers/customer_list.html', context)


# ── Create ────────────────────────────────────────────────────────────────────

@attendant_required
def customer_create(request):
    form = CustomerForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        customer = form.save(commit=False)
        customer.created_by = request.user
        customer.save()

        log_customer(
            request.user,
            f'Created customer: {customer}',
            object_type='Customer',
            object_id=customer.id,
            object_repr=str(customer),
            request=request,
        )
        messages.success(request, f'Customer "{customer}" added successfully.')

        # POS quick-add: return JSON if AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'customer': {
                    'id':   customer.id,
                    'name': customer.full_name,
                    'phone': customer.phone,
                },
            })

        return redirect('customers:detail', pk=customer.pk)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'errors': form.errors}, status=400)

    return render(request, 'customers/customer_form.html', {'form': form, 'action': 'Add'})


# ── Detail ────────────────────────────────────────────────────────────────────

@attendant_required
def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)

    recent_sales    = customer.sales.filter(locked=True).order_by('-created_at')[:10]
    credit_payments = customer.credit_payments.order_by('-created_at')[:10]
    credit_form     = CreditPaymentForm()

    context = {
        'customer':       customer,
        'recent_sales':   recent_sales,
        'credit_payments': credit_payments,
        'credit_form':    credit_form,
    }
    return render(request, 'customers/customer_detail.html', context)


# ── Edit ──────────────────────────────────────────────────────────────────────

@attendant_required
def customer_edit(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    form     = CustomerForm(request.POST or None, instance=customer)

    if request.method == 'POST' and form.is_valid():
        form.save()
        log_customer(
            request.user,
            f'Updated customer: {customer}',
            object_type='Customer',
            object_id=customer.id,
            object_repr=str(customer),
            request=request,
        )
        messages.success(request, f'Customer "{customer}" updated.')
        return redirect('customers:detail', pk=customer.pk)

    return render(request, 'customers/customer_form.html', {
        'form': form, 'customer': customer, 'action': 'Edit'
    })


# ── Deactivate (soft delete) ──────────────────────────────────────────────────

@owner_required
@require_POST
def customer_deactivate(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    customer.is_active = False
    customer.save(update_fields=['is_active', 'updated_at'])

    log_customer(
        request.user,
        f'Deactivated customer: {customer}',
        object_type='Customer',
        object_id=customer.id,
        object_repr=str(customer),
        level=AuditLog.LEVEL_WARNING,
        request=request,
    )
    messages.warning(request, f'Customer "{customer}" has been deactivated.')
    return redirect('customers:list')


# ── Credit payment ────────────────────────────────────────────────────────────

@attendant_required
@require_POST
def record_credit_payment(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    form     = CreditPaymentForm(request.POST)

    if form.is_valid():
        payment = form.save(commit=False)
        payment.customer    = customer
        payment.recorded_by = request.user
        payment.save()

        # Update the customer's credit balance
        customer.reduce_credit(payment.amount)

        log_customer(
            request.user,
            f'Credit payment of GH₵{payment.amount} recorded for {customer}',
            object_type='CreditPayment',
            object_id=payment.id,
            object_repr=str(payment),
            request=request,
        )
        messages.success(
            request,
            f'GH₵{payment.amount} credit payment recorded. '
            f'Remaining balance: GH₵{customer.credit_balance}.'
        )
    else:
        for field, errs in form.errors.items():
            for err in errs:
                messages.error(request, f'{field}: {err}')

    return redirect('customers:detail', pk=customer.pk)


# ── AJAX: POS customer search ─────────────────────────────────────────────────

@ajax_required
@attendant_required
@require_GET
def customer_search_ajax(request):
    """
    Called by the POS screen when the cashier types a customer name or phone.
    Returns JSON list of matching active customers.
    """
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'results': []})

    customers = Customer.objects.filter(is_active=True).filter(
        full_name__icontains=q
    ) | Customer.objects.filter(is_active=True).filter(
        phone__icontains=q
    ) | Customer.objects.filter(is_active=True).filter(
        company_name__icontains=q
    )
    customers = customers.distinct()[:10]

    results = [
        {
            'id':             c.id,
            'name':           c.full_name,
            'company':        c.company_name,
            'phone':          c.phone,
            'type':           c.get_customer_type_display(),
            'credit_balance': str(c.credit_balance),
            'loyalty_points': c.loyalty_points,
        }
        for c in customers
    ]
    return JsonResponse({'results': results})


# ── AJAX: customer quick-info for POS ─────────────────────────────────────────

@ajax_required
@attendant_required
@require_GET
def customer_info_ajax(request, pk):
    """Returns a single customer's key info as JSON for the POS panel."""
    customer = get_object_or_404(Customer, pk=pk, is_active=True)
    return JsonResponse({
        'id':               customer.id,
        'name':             customer.full_name,
        'company':          customer.company_name,
        'phone':            customer.phone,
        'type':             customer.customer_type,
        'credit_balance':   str(customer.credit_balance),
        'credit_limit':     str(customer.credit_limit),
        'available_credit': str(customer.available_credit),
        'loyalty_points':   customer.loyalty_points,
        'is_wholesale':     customer.customer_type == Customer.TYPE_WHOLESALE,
    })
