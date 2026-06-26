"""
reports/generator.py
All report data functions. Each returns a dict that views render
into the template, PDF, or CSV.
"""
from django.db.models import Sum, Count, Avg, Q, F, DecimalField
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal


def _date_range(params):
    today = date.today()
    date_from = params.get('date_from') or today.replace(day=1)
    date_to = params.get('date_to') or today
    if isinstance(date_from, str):
        from datetime import datetime
        date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
    if isinstance(date_to, str):
        from datetime import datetime
        date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
    return date_from, date_to


def sales_summary_report(params):
    from sales.models import Sale, SaleItem
    date_from, date_to = _date_range(params)

    sales = Sale.objects.filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
    )

    totals = sales.aggregate(
        total_sales=Count('id'),
        gross_revenue=Sum('total'),
        total_discounts=Sum('discount_amount'),
    )

    items = SaleItem.objects.filter(
        sale__in=sales
    ).aggregate(
        total_revenue=Sum(F('quantity') * F('unit_price'), output_field=DecimalField()),
        total_cost=Sum(F('quantity') * F('cost_price'), output_field=DecimalField()),
    )
    gross_profit = (items['total_revenue'] or 0) - (items['total_cost'] or 0)

    daily = sales.values('created_at__date').annotate(
        count=Count('id'),
        revenue=Sum('total'),
    ).order_by('created_at__date')

    return {
        'report_type': 'sales_summary',
        'date_from': date_from,
        'date_to': date_to,
        'total_transactions': totals['total_sales'] or 0,
        'gross_revenue': totals['gross_revenue'] or 0,
        'total_discounts': totals['total_discounts'] or 0,
        'gross_profit': gross_profit,
        'daily_breakdown': list(daily),
    }


def sales_by_product_report(params):
    from sales.models import SaleItem
    date_from, date_to = _date_range(params)

    rows = SaleItem.objects.filter(
        sale__created_at__date__gte=date_from,
        sale__created_at__date__lte=date_to,
    ).values(
        'product_id', 'product_name', 'product_brand'
    ).annotate(
        units_sold=Sum('quantity'),
        total_revenue=Sum(F('quantity') * F('unit_price'), output_field=DecimalField()),
        total_cost=Sum(F('quantity') * F('cost_price'), output_field=DecimalField()),
        transaction_count=Count('sale', distinct=True),
    ).order_by('-total_revenue')

    rows = list(rows)
    for row in rows:
        row['gross_profit'] = (row['total_revenue'] or 0) - (row['total_cost'] or 0)

    return {
        'report_type': 'sales_by_product',
        'date_from': date_from,
        'date_to': date_to,
        'rows': rows,
        'grand_total_revenue': sum(r['total_revenue'] or 0 for r in rows),
        'grand_total_profit': sum(r['gross_profit'] for r in rows),
    }


def sales_by_attendant_report(params):
    from sales.models import Sale
    date_from, date_to = _date_range(params)

    rows = Sale.objects.filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
    ).values(
        'attendant__id', 'attendant__full_name', 'attendant__username'
    ).annotate(
        transaction_count=Count('id'),
        total_revenue=Sum('total'),
        total_discounts=Sum('discount_amount'),
    ).order_by('-total_revenue')

    return {
        'report_type': 'sales_by_attendant',
        'date_from': date_from,
        'date_to': date_to,
        'rows': list(rows),
    }


def sales_by_customer_report(params):
    from sales.models import Sale
    date_from, date_to = _date_range(params)

    rows = Sale.objects.filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
    ).values(
        'customer__id', 'customer_name'
    ).annotate(
        transaction_count=Count('id'),
        total_spent=Sum('total'),
    ).order_by('-total_spent')[:50]

    return {
        'report_type': 'sales_by_customer',
        'date_from': date_from,
        'date_to': date_to,
        'rows': list(rows),
    }


def inventory_status_report(params):
    from products.models import Product

    category_id = params.get('category_id')
    show_low_stock_only = params.get('low_stock_only', False)

    products = Product.objects.filter(is_active=True).select_related('category')
    if category_id:
        products = products.filter(category_id=category_id)

    rows = []
    for product in products:
        try:
            sl = product.stock_level
            current_qty = sl.current_quantity
        except Exception:
            current_qty = 0

        is_low = current_qty <= product.reorder_point
        if show_low_stock_only and not is_low:
            continue

        rows.append({
            'product': product,
            'current_qty': current_qty,
            'reorder_point': product.reorder_point,
            'is_low': is_low,
            'stock_value': current_qty * product.cost_price,
        })

    total_value = sum(r['stock_value'] for r in rows)
    return {
        'report_type': 'inventory_status',
        'rows': rows,
        'total_value': total_value,
        'low_stock_count': sum(1 for r in rows if r['is_low']),
    }


def low_stock_report(params):
    params['low_stock_only'] = True
    return inventory_status_report(params)


def expense_summary_report(params):
    from expenses.models import Expense
    date_from, date_to = _date_range(params)

    expenses = Expense.objects.filter(
        expense_date__gte=date_from,
        expense_date__lte=date_to,
        status='approved',
    )

    totals = expenses.aggregate(
        total_amount=Sum('amount'),
        count=Count('id'),
    )

    by_category = expenses.values(
        'category__name', 'category__icon'
    ).annotate(
        total=Sum('amount'),
        count=Count('id'),
    ).order_by('-total')

    by_method = expenses.values('payment_method').annotate(
        total=Sum('amount'),
    ).order_by('-total')

    return {
        'report_type': 'expense_summary',
        'date_from': date_from,
        'date_to': date_to,
        'total_amount': totals['total_amount'] or 0,
        'total_count': totals['count'] or 0,
        'by_category': list(by_category),
        'by_method': list(by_method),
    }


def profit_loss_report(params):
    from sales.models import Sale, SaleItem
    from expenses.models import Expense

    date_from, date_to = _date_range(params)

    sales = Sale.objects.filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
    )
    revenue = sales.aggregate(total=Sum('total'))['total'] or 0
    discounts_given = sales.aggregate(total=Sum('discount_amount'))['total'] or 0

    items = SaleItem.objects.filter(
        sale__in=sales
    ).aggregate(
        cogs=Sum(F('quantity') * F('cost_price'), output_field=DecimalField())
    )
    cogs = items['cogs'] or 0
    gross_profit = revenue - cogs

    operating_expenses = Expense.objects.filter(
        expense_date__gte=date_from,
        expense_date__lte=date_to,
        status='approved',
    ).aggregate(total=Sum('amount'))['total'] or 0

    net_profit = gross_profit - operating_expenses

    return {
        'report_type': 'profit_loss',
        'date_from': date_from,
        'date_to': date_to,
        'revenue': revenue,
        'discounts_given': discounts_given,
        'net_revenue': revenue - discounts_given,
        'cogs': cogs,
        'gross_profit': gross_profit,
        'gross_margin_pct': round((gross_profit / revenue * 100), 1) if revenue else 0,
        'operating_expenses': operating_expenses,
        'net_profit': net_profit,
        'net_margin_pct': round((net_profit / revenue * 100), 1) if revenue else 0,
    }


def purchase_summary_report(params):
    from purchases.models import PurchaseOrder
    date_from, date_to = _date_range(params)

    pos = PurchaseOrder.objects.filter(
        order_date__gte=date_from,
        order_date__lte=date_to,
    )

    totals = pos.aggregate(
        total_orders=Count('id'),
        total_value=Sum('grand_total'),
        total_paid=Sum('amount_paid'),
    )

    by_supplier = pos.values('supplier__name').annotate(
        order_count=Count('id'),
        total_value=Sum('grand_total'),
    ).order_by('-total_value')

    by_status = pos.values('status').annotate(
        count=Count('id'),
        total=Sum('grand_total'),
    )

    return {
        'report_type': 'purchase_summary',
        'date_from': date_from,
        'date_to': date_to,
        'total_orders': totals['total_orders'] or 0,
        'total_value': totals['total_value'] or 0,
        'total_paid': totals['total_paid'] or 0,
        'total_outstanding': (totals['total_value'] or 0) - (totals['total_paid'] or 0),
        'by_supplier': list(by_supplier),
        'by_status': list(by_status),
    }


def customer_credit_report(params):
    from customers.models import Customer
    customers = Customer.objects.filter(
        is_active=True,
        credit_balance__gt=0
    ).order_by('-credit_balance')

    total_outstanding = customers.aggregate(
        total=Sum('credit_balance')
    )['total'] or 0

    return {
        'report_type': 'customer_credit',
        'customers': list(customers.values(
            'id', 'full_name', 'phone', 'customer_type',
            'credit_balance', 'credit_limit'
        )),
        'total_outstanding': total_outstanding,
        'total_customers_with_credit': customers.count(),
    }


def returns_summary_report(params):
    from returns.models import Return
    date_from, date_to = _date_range(params)

    returns = Return.objects.filter(
        return_date__gte=date_from,
        return_date__lte=date_to,
    )

    totals = returns.aggregate(
        count=Count('id'),
        total_refunded=Sum('refund_amount'),
    )

    by_reason = returns.values('reason').annotate(
        count=Count('id'),
        total_refunded=Sum('refund_amount'),
    ).order_by('-count')

    by_resolution = returns.filter(status='resolved').values('resolution').annotate(
        count=Count('id'),
    ).order_by('-count')

    return {
        'report_type': 'returns_summary',
        'date_from': date_from,
        'date_to': date_to,
        'total_count': totals['count'] or 0,
        'total_refunded': totals['total_refunded'] or 0,
        'by_reason': list(by_reason),
        'by_resolution': list(by_resolution),
    }


def attendant_performance_report(params):
    from sales.models import Sale
    date_from, date_to = _date_range(params)

    rows = Sale.objects.filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
    ).values(
        'attendant__id', 'attendant__full_name', 'attendant__username'
    ).annotate(
        total_sales=Count('id'),
        total_revenue=Sum('total'),
        total_discounts=Sum('discount_amount'),
        avg_sale_value=Avg('total'),
    ).order_by('-total_revenue')

    return {
        'report_type': 'attendant_performance',
        'date_from': date_from,
        'date_to': date_to,
        'rows': list(rows),
    }


REPORT_FUNCTIONS = {
    'sales_summary': sales_summary_report,
    'sales_by_product': sales_by_product_report,
    'sales_by_attendant': sales_by_attendant_report,
    'sales_by_customer': sales_by_customer_report,
    'inventory_status': inventory_status_report,
    'low_stock': low_stock_report,
    'expense_summary': expense_summary_report,
    'profit_loss': profit_loss_report,
    'purchase_summary': purchase_summary_report,
    'customer_credit': customer_credit_report,
    'returns_summary': returns_summary_report,
    'attendant_performance': attendant_performance_report,
}


def run_report(report_type, params):
    fn = REPORT_FUNCTIONS.get(report_type)
    if fn is None:
        raise ValueError(f"Unknown report type: {report_type}")
    return fn(params)