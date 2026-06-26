from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import owner_required, attendant_required
from audit.models import AuditLog
from audit.utils import log_action
from .forms import ExpenseForm, ExpenseCategoryForm, ExpenseRejectForm
from .models import Expense, ExpenseCategory


# ── Expense list ──────────────────────────────────────────────────────────────

@attendant_required
def expense_list(request):
    expenses = Expense.objects.select_related('category', 'recorded_by', 'approved_by')

    # ── Filters ───────────────────────────────────────────────────────────────
    q          = request.GET.get('q', '').strip()
    category   = request.GET.get('category', '').strip()
    status     = request.GET.get('status', '').strip()
    date_from  = request.GET.get('date_from', '').strip()
    date_to    = request.GET.get('date_to', '').strip()
    month      = request.GET.get('month', '').strip()  # YYYY-MM quick filter

    if q:
        expenses = expenses.filter(title__icontains=q) | \
                   expenses.filter(notes__icontains=q) | \
                   expenses.filter(reference__icontains=q)

    if category:
        expenses = expenses.filter(category_id=category)

    if status:
        expenses = expenses.filter(status=status)

    if month:
        try:
            year, mon = month.split('-')
            expenses = expenses.filter(expense_date__year=int(year),
                                       expense_date__month=int(mon))
        except (ValueError, AttributeError):
            pass

    if date_from:
        try:
            expenses = expenses.filter(expense_date__gte=date_from)
        except Exception:
            pass

    if date_to:
        try:
            expenses = expenses.filter(expense_date__lte=date_to)
        except Exception:
            pass

    # Attendants only see their own expenses; owners see all
    if not request.user.is_owner:
        expenses = expenses.filter(recorded_by=request.user)

    # ── Totals for the filtered set ───────────────────────────────────────────
    approved_total = expenses.filter(
        status=Expense.STATUS_APPROVED
    ).aggregate(t=Sum('amount'))['t'] or Decimal('0.00')

    pending_total  = expenses.filter(
        status=Expense.STATUS_PENDING
    ).aggregate(t=Sum('amount'))['t'] or Decimal('0.00')

    paginator = Paginator(expenses, 25)
    page_obj  = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj':      page_obj,
        'categories':    ExpenseCategory.objects.filter(is_active=True),
        'statuses':      Expense.STATUS_CHOICES,
        'approved_total': approved_total,
        'pending_total':  pending_total,
        'filters': {
            'q': q, 'category': category, 'status': status,
            'date_from': date_from, 'date_to': date_to, 'month': month,
        },
    }
    return render(request, 'expenses/expense_list.html', context)


# ── Create ────────────────────────────────────────────────────────────────────

@attendant_required
def expense_create(request):
    form = ExpenseForm(request.POST or None, request.FILES or None)

    if request.method == 'POST' and form.is_valid():
        expense = form.save(commit=False)
        expense.recorded_by = request.user

        # Owners' expenses are auto-approved; attendants' need approval
        if request.user.is_owner:
            expense.status      = Expense.STATUS_APPROVED
            expense.approved_by = request.user
            from django.utils import timezone
            expense.approved_at = timezone.now()

        expense.save()

        log_action(
            user=request.user,
            category=AuditLog.CATEGORY_EXPENSE,
            action=f'Recorded expense: {expense.title} — GH₵{expense.amount}',
            object_type='Expense',
            object_id=expense.id,
            object_repr=str(expense),
            request=request,
        )
        messages.success(request, f'Expense "{expense.title}" recorded.')
        return redirect('expenses:list')

    return render(request, 'expenses/expense_form.html', {'form': form, 'action': 'Record'})


# ── Edit ──────────────────────────────────────────────────────────────────────

@attendant_required
def expense_edit(request, pk):
    expense = get_object_or_404(Expense, pk=pk)

    # Attendants can only edit their own pending expenses
    if not request.user.is_owner:
        if expense.recorded_by != request.user or not expense.is_pending:
            messages.error(request, 'You can only edit your own pending expenses.')
            return redirect('expenses:list')

    form = ExpenseForm(request.POST or None, request.FILES or None, instance=expense)

    if request.method == 'POST' and form.is_valid():
        updated = form.save(commit=False)
        # Editing resets approval if it was already approved
        if updated.status == Expense.STATUS_APPROVED and not request.user.is_owner:
            updated.status      = Expense.STATUS_PENDING
            updated.approved_by = None
            updated.approved_at = None
        updated.save()

        log_action(
            user=request.user,
            category=AuditLog.CATEGORY_EXPENSE,
            action=f'Updated expense: {expense.title}',
            object_type='Expense',
            object_id=expense.id,
            object_repr=str(expense),
            request=request,
        )
        messages.success(request, f'Expense "{expense.title}" updated.')
        return redirect('expenses:list')

    return render(request, 'expenses/expense_form.html', {
        'form': form, 'expense': expense, 'action': 'Edit'
    })


# ── Approve ───────────────────────────────────────────────────────────────────

@owner_required
@require_POST
def expense_approve(request, pk):
    expense = get_object_or_404(Expense, pk=pk, status=Expense.STATUS_PENDING)
    expense.approve(request.user)

    log_action(
        user=request.user,
        category=AuditLog.CATEGORY_EXPENSE,
        action=f'Approved expense: {expense.title} — GH₵{expense.amount}',
        object_type='Expense',
        object_id=expense.id,
        object_repr=str(expense),
        request=request,
    )
    messages.success(request, f'Expense "{expense.title}" approved.')
    return redirect('expenses:list')


# ── Reject ────────────────────────────────────────────────────────────────────

@owner_required
@require_POST
def expense_reject(request, pk):
    expense = get_object_or_404(Expense, pk=pk, status=Expense.STATUS_PENDING)
    form    = ExpenseRejectForm(request.POST)

    reason = ''
    if form.is_valid():
        reason = form.cleaned_data.get('reason', '')

    expense.reject(request.user, reason)

    log_action(
        user=request.user,
        category=AuditLog.CATEGORY_EXPENSE,
        action=f'Rejected expense: {expense.title} — GH₵{expense.amount}',
        object_type='Expense',
        object_id=expense.id,
        object_repr=str(expense),
        level=AuditLog.LEVEL_WARNING,
        request=request,
    )
    messages.warning(request, f'Expense "{expense.title}" rejected.')
    return redirect('expenses:list')


# ── Delete ────────────────────────────────────────────────────────────────────

@owner_required
@require_POST
def expense_delete(request, pk):
    expense = get_object_or_404(Expense, pk=pk)
    title   = expense.title
    expense.delete()

    log_action(
        user=request.user,
        category=AuditLog.CATEGORY_EXPENSE,
        action=f'Deleted expense: {title}',
        level=AuditLog.LEVEL_WARNING,
        request=request,
    )
    messages.success(request, f'Expense "{title}" deleted.')
    return redirect('expenses:list')


# ── Category management (owner only) ─────────────────────────────────────────

@owner_required
def category_list(request):
    categories = ExpenseCategory.objects.all()
    return render(request, 'expenses/category_list.html', {'categories': categories})


@owner_required
def category_create(request):
    form = ExpenseCategoryForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        cat = form.save()
        messages.success(request, f'Category "{cat.name}" created.')
        return redirect('expenses:category_list')
    return render(request, 'expenses/category_form.html', {'form': form, 'action': 'Create'})


@owner_required
def category_edit(request, pk):
    cat  = get_object_or_404(ExpenseCategory, pk=pk)
    form = ExpenseCategoryForm(request.POST or None, instance=cat)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Category "{cat.name}" updated.')
        return redirect('expenses:category_list')
    return render(request, 'expenses/category_form.html', {
        'form': form, 'category': cat, 'action': 'Edit'
    })