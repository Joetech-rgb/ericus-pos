from decimal import Decimal
from django.db.models import Sum, Count, Q
from django.utils import timezone
from .models import Expense, ExpenseCategory


def get_expense_summary(month=None, year=None):
    """
    Returns totals for the dashboard widget.
    Defaults to the current month if no period given.
    """
    now = timezone.now()
    year  = year  or now.year
    month = month or now.month

    qs = Expense.objects.filter(
        expense_date__year=year,
        expense_date__month=month,
    )

    agg = qs.aggregate(
        total_approved=Sum('amount', filter=Q(status=Expense.STATUS_APPROVED)),
        total_pending=Sum('amount',  filter=Q(status=Expense.STATUS_PENDING)),
        total_rejected=Sum('amount', filter=Q(status=Expense.STATUS_REJECTED)),
        count_approved=Count('id',   filter=Q(status=Expense.STATUS_APPROVED)),
        count_pending=Count('id',    filter=Q(status=Expense.STATUS_PENDING)),
    )

    return {
        'month':          month,
        'year':           year,
        'total_approved': agg['total_approved']  or Decimal('0.00'),
        'total_pending':  agg['total_pending']   or Decimal('0.00'),
        'total_rejected': agg['total_rejected']  or Decimal('0.00'),
        'count_approved': agg['count_approved']  or 0,
        'count_pending':  agg['count_pending']   or 0,
    }


def get_expenses_by_category(month=None, year=None):
    """
    Breakdown of approved expenses by category for the current period.
    Returns a list of dicts sorted by amount descending — used in reports/charts.
    """
    now   = timezone.now()
    year  = year  or now.year
    month = month or now.month

    rows = (
        Expense.objects
        .filter(
            status=Expense.STATUS_APPROVED,
            expense_date__year=year,
            expense_date__month=month,
        )
        .values('category__name', 'category__icon')
        .annotate(total=Sum('amount'), count=Count('id'))
        .order_by('-total')
    )
    return list(rows)


def get_monthly_expense_trend(months=6):
    """
    Returns approved expense totals for the last N months.
    Used to draw the expense trend line on the dashboard chart.
    """
    from datetime import date
    import calendar

    today  = timezone.now().date()
    result = []

    for i in range(months - 1, -1, -1):
        # Step back i months
        month = today.month - i
        year  = today.year
        while month <= 0:
            month += 12
            year  -= 1

        total = Expense.objects.filter(
            status=Expense.STATUS_APPROVED,
            expense_date__year=year,
            expense_date__month=month,
        ).aggregate(t=Sum('amount'))['t'] or Decimal('0.00')

        result.append({
            'label': date(year, month, 1).strftime('%b %Y'),
            'total': float(total),
        })

    return result


def get_pending_expenses():
    """All expenses awaiting owner approval — for the dashboard alert."""
    return Expense.objects.filter(
        status=Expense.STATUS_PENDING
    ).select_related('category', 'recorded_by').order_by('created_at')


def seed_default_categories():
    """
    Creates the standard expense categories on first setup.
    Call from a post-migrate signal or a management command.
    """
    defaults = [
        ('Rent',           'fa-building',      'Monthly shop rent'),
        ('Utilities',      'fa-bolt',           'Electricity, water, internet'),
        ('Salaries',       'fa-users',          'Staff wages and allowances'),
        ('Transport',      'fa-truck',          'Delivery and transport costs'),
        ('Repairs',        'fa-tools',          'Equipment and shop repairs'),
        ('Stationery',     'fa-pen',            'Office and shop supplies'),
        ('Marketing',      'fa-bullhorn',       'Adverts, flyers, promotions'),
        ('Miscellaneous',  'fa-ellipsis-h',     'Other uncategorised expenses'),
    ]

    for name, icon, desc in defaults:
        ExpenseCategory.objects.get_or_create(
            name=name,
            defaults={'icon': icon, 'description': desc, 'is_active': True},
        )