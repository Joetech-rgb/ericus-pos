"""
reports/charts.py
Returns Python dicts that serialize directly to Chart.js config objects.
"""
from datetime import date, timedelta
from django.db.models import Sum, Count, F, DecimalField, ExpressionWrapper


def sales_trend_chart(date_from, date_to):
    from sales.models import Sale

    sales_qs = Sale.objects.filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
    ).values('created_at__date').annotate(
        revenue=Sum('total'),
        count=Count('id'),
    ).order_by('created_at__date')

    labels = []
    revenue_data = []
    count_data = []

    day = date_from
    daily_map = {row['created_at__date']: row for row in sales_qs}
    while day <= date_to:
        labels.append(day.strftime('%d %b'))
        row = daily_map.get(day, {})
        revenue_data.append(float(row.get('revenue', 0) or 0))
        count_data.append(row.get('count', 0))
        day += timedelta(days=1)

    return {
        'type': 'line',
        'data': {
            'labels': labels,
            'datasets': [
                {
                    'label': 'Revenue (GH\u20b5)',
                    'data': revenue_data,
                    'borderColor': '#0d6efd',
                    'backgroundColor': 'rgba(13,110,253,0.1)',
                    'fill': True,
                    'tension': 0.3,
                    'yAxisID': 'y',
                },
                {
                    'label': 'Transactions',
                    'data': count_data,
                    'borderColor': '#198754',
                    'backgroundColor': 'rgba(25,135,84,0.1)',
                    'fill': False,
                    'tension': 0.3,
                    'yAxisID': 'y1',
                },
            ],
        },
        'options': {
            'responsive': True,
            'interaction': {'mode': 'index', 'intersect': False},
            'scales': {
                'y': {'position': 'left', 'title': {'display': True, 'text': 'Revenue (GH\u20b5)'}},
                'y1': {'position': 'right', 'title': {'display': True, 'text': 'Transactions'}, 'grid': {'drawOnChartArea': False}},
            },
        },
    }


def top_products_chart(date_from, date_to, limit=10):
    from sales.models import SaleItem

    rows = SaleItem.objects.filter(
        sale__created_at__date__gte=date_from,
        sale__created_at__date__lte=date_to,
    ).values('product_name').annotate(
        revenue=Sum(
            ExpressionWrapper(F('quantity') * F('unit_price'), output_field=DecimalField())
        ),
        units=Sum('quantity'),
    ).order_by('-revenue')[:limit]

    labels = [r['product_name'] for r in rows]
    revenues = [float(r['revenue'] or 0) for r in rows]

    return {
        'type': 'bar',
        'data': {
            'labels': labels,
            'datasets': [{
                'label': 'Revenue (GH\u20b5)',
                'data': revenues,
                'backgroundColor': [
                    '#0d6efd', '#198754', '#ffc107', '#dc3545', '#0dcaf0',
                    '#6f42c1', '#fd7e14', '#20c997', '#d63384', '#6c757d',
                ][:len(labels)],
            }],
        },
        'options': {
            'indexAxis': 'y',
            'responsive': True,
            'plugins': {'legend': {'display': False}},
        },
    }


def expense_by_category_chart(date_from, date_to):
    from expenses.models import Expense

    rows = Expense.objects.filter(
        expense_date__gte=date_from,
        expense_date__lte=date_to,
        status='approved',
    ).values('category__name').annotate(
        total=Sum('amount')
    ).order_by('-total')

    labels = [r['category__name'] or 'Uncategorised' for r in rows]
    data = [float(r['total'] or 0) for r in rows]

    colors = [
        '#0d6efd', '#198754', '#ffc107', '#dc3545', '#0dcaf0',
        '#6f42c1', '#fd7e14', '#20c997', '#d63384', '#6c757d',
    ]

    return {
        'type': 'doughnut',
        'data': {
            'labels': labels,
            'datasets': [{
                'data': data,
                'backgroundColor': colors[:len(labels)],
            }],
        },
        'options': {
            'responsive': True,
            'plugins': {'legend': {'position': 'right'}},
        },
    }


def monthly_profit_chart(months=6):
    from sales.models import Sale, SaleItem
    from expenses.models import Expense

    labels = []
    profits = []
    expenses_data = []

    today = date.today()
    for i in range(months - 1, -1, -1):
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1)
        else:
            month_end = date(year, month + 1, 1)

        labels.append(month_start.strftime('%b %Y'))

        sales_qs = Sale.objects.filter(
            created_at__date__gte=month_start,
            created_at__date__lt=month_end,
        )
        items = SaleItem.objects.filter(sale__in=sales_qs).aggregate(
            rev=Sum(ExpressionWrapper(F('quantity') * F('unit_price'), output_field=DecimalField())),
            cost=Sum(ExpressionWrapper(F('quantity') * F('cost_price'), output_field=DecimalField())),
        )
        gross_profit = float((items['rev'] or 0) - (items['cost'] or 0))
        profits.append(gross_profit)

        exp = Expense.objects.filter(
            expense_date__gte=month_start,
            expense_date__lt=month_end,
            status='approved',
        ).aggregate(total=Sum('amount'))['total'] or 0
        expenses_data.append(float(exp))

    return {
        'type': 'bar',
        'data': {
            'labels': labels,
            'datasets': [
                {
                    'label': 'Gross Profit',
                    'data': profits,
                    'backgroundColor': 'rgba(25,135,84,0.7)',
                },
                {
                    'label': 'Expenses',
                    'data': expenses_data,
                    'backgroundColor': 'rgba(220,53,69,0.7)',
                },
            ],
        },
        'options': {
            'responsive': True,
            'scales': {
                'x': {'stacked': False},
                'y': {'title': {'display': True, 'text': 'GH\u20b5'}},
            },
        },
    }


def payment_method_chart(date_from, date_to):
    """Pie chart — sales by payment method, using Sale.payment_method directly."""
    from sales.models import Sale

    # FIX: was querying Payment model which doesn't exist — use Sale.payment_method
    rows = Sale.objects.filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
    ).values('payment_method').annotate(
        total=Sum('total'),
        count=Count('id'),
    ).order_by('-total')

    method_labels = {
        'cash':             'Cash',
        'momo':             'Mobile Money',
        'bank_transfer':    'Bank Transfer',
        'credit':           'Credit',
        'split':            'Split',
        'wholesale_credit': 'Wholesale Credit',
    }

    labels = [method_labels.get(r['payment_method'], r['payment_method']) for r in rows]
    data   = [float(r['total'] or 0) for r in rows]
    colors = ['#198754', '#ffc107', '#0d6efd', '#dc3545', '#6f42c1', '#fd7e14']

    return {
        'type': 'pie',
        'data': {
            'labels': labels,
            'datasets': [{
                'data': data,
                'backgroundColor': colors[:len(labels)],
            }],
        },
        'options': {
            'responsive': True,
            'plugins': {'legend': {'position': 'right'}},
        },
    }