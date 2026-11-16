import csv
import json
from datetime import date

from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse, JsonResponse

from accounts.decorators import owner_required
from audit.utils import log_report
from .generator import run_report, REPORT_FUNCTIONS
from .charts import (
    sales_trend_chart, top_products_chart, expense_by_category_chart,
    monthly_profit_chart, payment_method_chart,
)
from .pdf_builder import (
    build_sales_summary_pdf, build_profit_loss_pdf,
    build_inventory_pdf, pdf_response,
)


def _resolve_range(request, today):
    """Date range for the reports dashboard: custom dates win, then presets."""
    from datetime import timedelta
    preset = (request.GET.get('preset') or '').strip().lower()
    raw_from = (request.GET.get('date_from') or '').strip()
    raw_to = (request.GET.get('date_to') or '').strip()
    if raw_from or raw_to:
        try:
            start = date.fromisoformat(raw_from) if raw_from else today.replace(day=1)
            end = date.fromisoformat(raw_to) if raw_to else today
            if start > end:
                start, end = end, start
            return start, end, 'custom'
        except ValueError:
            pass
    if preset == 'today':
        return today, today, preset
    if preset == 'yesterday':
        y = today - timedelta(days=1)
        return y, y, preset
    if preset == 'week':
        return today - timedelta(days=today.weekday()), today, preset
    if preset == 'quarter':
        q = (today.month - 1) // 3 * 3 + 1
        return today.replace(month=q, day=1), today, preset
    if preset == 'year':
        return today.replace(month=1, day=1), today, preset
    return today.replace(day=1), today, 'month'


def _parse_date_params(request):
    today = date.today()
    date_from = request.GET.get('date_from') or today.replace(day=1).isoformat()
    date_to = request.GET.get('date_to') or today.isoformat()
    return {'date_from': date_from, 'date_to': date_to}


# ─── Dashboard ────────────────────────────────────────────────────────────────

@owner_required
def reports_dashboard(request):
    """Overview page — links to all reports with quick stats."""
    today = date.today()
    month_start = today.replace(day=1)

    # FIX: pass ISO strings, not date objects — run_report expects strings
    start, end, preset = _resolve_range(request, today)
    month_start = start
    params = {
        'date_from': start.isoformat(),
        'date_to': end.isoformat(),
    }

    try:
        pl = run_report('profit_loss', params)
    except Exception:
        pl = {}

    try:
        inv = run_report('low_stock', {})
    except Exception:
        inv = {'low_stock_count': 0}

    try:
        daily_rows = run_report('sales_summary', params).get('daily_breakdown', [])
    except Exception:
        daily_rows = []

    profit_chart = monthly_profit_chart(6)
    payment_chart = payment_method_chart(start, end)

    log_report(request.user, "Viewed reports dashboard", request=request)

    return render(request, 'reports/dashboard.html', {
        'pl': pl,
        'inv': inv,
        'profit_chart_json': json.dumps(profit_chart),
        'payment_chart_json': json.dumps(payment_chart),
        'today': today,
        'month_start': month_start,
        'date_from': start.isoformat(),
        'date_to': end.isoformat(),
        'preset': preset,
        'daily_rows': daily_rows,
    })


# ─── Sales Reports ────────────────────────────────────────────────────────────

@owner_required
def sales_summary(request):
    params = _parse_date_params(request)
    fmt = request.GET.get('format', 'screen')
    data = run_report('sales_summary', params)

    trend_chart = sales_trend_chart(
        date.fromisoformat(params['date_from']),
        date.fromisoformat(params['date_to']),
    )
    top_chart = top_products_chart(
        date.fromisoformat(params['date_from']),
        date.fromisoformat(params['date_to']),
    )

    if fmt == 'pdf':
        buffer = build_sales_summary_pdf(data)
        if buffer:
            return pdf_response(buffer, 'sales_summary.pdf')
        messages.error(request, "PDF generation failed. ReportLab not installed.")

    if fmt == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="sales_summary.csv"'
        writer = csv.writer(response)
        writer.writerow(['Date', 'Transactions', 'Revenue'])
        for row in data.get('daily_breakdown', []):
            writer.writerow([row['created_at__date'], row['count'], row['revenue']])
        return response

    log_report(request.user, f"Sales Summary {params['date_from']} to {params['date_to']}", request=request)
    return render(request, 'reports/sales_summary.html', {
        'data': data,
        'trend_chart_json': json.dumps(trend_chart),
        'top_chart_json': json.dumps(top_chart),
        'date_from': params['date_from'],
        'date_to': params['date_to'],
    })


@owner_required
def sales_by_product(request):
    params = _parse_date_params(request)
    fmt = request.GET.get('format', 'screen')
    data = run_report('sales_by_product', params)

    if fmt == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="sales_by_product.csv"'
        writer = csv.writer(response)
        writer.writerow(['Product', 'Brand', 'Units Sold', 'Revenue (GH₵)', 'COGS (GH₵)', 'Gross Profit (GH₵)'])
        for row in data['rows']:
            writer.writerow([
                row['product_name_at_sale'], row['product_brand_at_sale'],
                row['units_sold'], row['total_revenue'], row['total_cost'], row['gross_profit'],
            ])
        return response

    log_report(request.user, f"Sales by Product {params['date_from']} to {params['date_to']}", request=request)
    return render(request, 'reports/sales_by_product.html', {
        'data': data,
        'date_from': params['date_from'],
        'date_to': params['date_to'],
    })


@owner_required
def sales_by_attendant(request):
    params = _parse_date_params(request)
    data = run_report('sales_by_attendant', params)
    log_report(request.user, "Sales by Attendant report viewed", request=request)
    return render(request, 'reports/sales_by_attendant.html', {
        'data': data,
        'date_from': params['date_from'],
        'date_to': params['date_to'],
    })


# ─── Inventory Reports ────────────────────────────────────────────────────────

@owner_required
def inventory_status(request):
    params = {}
    params['category_id'] = request.GET.get('category_id') or None
    params['low_stock_only'] = request.GET.get('low_stock_only') == '1'
    fmt = request.GET.get('format', 'screen')
    data = run_report('inventory_status', params)

    if fmt == 'pdf':
        buffer = build_inventory_pdf(data)
        if buffer:
            return pdf_response(buffer, 'inventory_status.pdf')

    if fmt == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="inventory.csv"'
        writer = csv.writer(response)
        writer.writerow(['Product', 'Category', 'In Stock', 'Reorder Point', 'Status', 'Stock Value'])
        for row in data['rows']:
            p = row['product']
            writer.writerow([
                p.name, p.category.name if p.category else '',
                row['current_qty'], row['reorder_point'],
                'LOW' if row['is_low'] else 'OK', row['stock_value'],
            ])
        return response

    from products.models import Category
    log_report(request.user, "Inventory Status report viewed", request=request)
    return render(request, 'reports/inventory_status.html', {
        'data': data,
        'categories': Category.objects.filter(is_active=True),
        'selected_category': params['category_id'],
        'low_stock_only': params['low_stock_only'],
    })


# ─── Expense Report ───────────────────────────────────────────────────────────

@owner_required
def expense_summary(request):
    params = _parse_date_params(request)
    data = run_report('expense_summary', params)

    exp_chart = expense_by_category_chart(
        date.fromisoformat(params['date_from']),
        date.fromisoformat(params['date_to']),
    )

    if request.GET.get('format') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="expenses.csv"'
        writer = csv.writer(response)
        writer.writerow(['Category', 'Count', 'Total (GH₵)'])
        for row in data['by_category']:
            writer.writerow([row['category__name'], row['count'], row['total']])
        return response

    log_report(request.user, f"Expense Summary {params['date_from']} to {params['date_to']}", request=request)
    return render(request, 'reports/expense_summary.html', {
        'data': data,
        'exp_chart_json': json.dumps(exp_chart),
        'date_from': params['date_from'],
        'date_to': params['date_to'],
    })


# ─── Profit & Loss ────────────────────────────────────────────────────────────

@owner_required
def profit_loss(request):
    params = _parse_date_params(request)
    data = run_report('profit_loss', params)
    fmt = request.GET.get('format', 'screen')

    if fmt == 'pdf':
        buffer = build_profit_loss_pdf(data)
        if buffer:
            return pdf_response(buffer, 'profit_loss.pdf')

    log_report(request.user, f"P&L {params['date_from']} to {params['date_to']}", request=request)
    return render(request, 'reports/profit_loss.html', {
        'data': data,
        'date_from': params['date_from'],
        'date_to': params['date_to'],
    })


# ─── Purchase Report ──────────────────────────────────────────────────────────

@owner_required
def purchase_summary(request):
    params = _parse_date_params(request)
    data = run_report('purchase_summary', params)
    log_report(request.user, "Purchase Summary report viewed", request=request)
    return render(request, 'reports/purchase_summary.html', {
        'data': data,
        'date_from': params['date_from'],
        'date_to': params['date_to'],
    })


# ─── Other Reports ────────────────────────────────────────────────────────────

@owner_required
def customer_credit(request):
    data = run_report('customer_credit', {})
    log_report(request.user, "Customer Credit report viewed", request=request)

    if request.GET.get('format') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="customer_credit.csv"'
        writer = csv.writer(response)
        writer.writerow(['Name', 'Phone', 'Type', 'Credit Balance (GH₵)', 'Credit Limit (GH₵)'])
        for c in data['customers']:
            writer.writerow([c['full_name'], c['phone'], c['customer_type'], c['credit_balance'], c['credit_limit']])
        return response

    return render(request, 'reports/customer_credit.html', {'data': data})


@owner_required
def returns_summary(request):
    params = _parse_date_params(request)
    data = run_report('returns_summary', params)
    log_report(request.user, "Returns Summary report viewed", request=request)
    return render(request, 'reports/returns_summary.html', {
        'data': data,
        'date_from': params['date_from'],
        'date_to': params['date_to'],
    })


@owner_required
def attendant_performance(request):
    params = _parse_date_params(request)
    data = run_report('attendant_performance', params)
    log_report(request.user, "Attendant Performance report viewed", request=request)
    return render(request, 'reports/attendant_performance.html', {
        'data': data,
        'date_from': params['date_from'],
        'date_to': params['date_to'],
    })


# ─── Chart Data AJAX endpoints ────────────────────────────────────────────────

@owner_required
def chart_data_ajax(request):
    """AJAX endpoint — returns any chart as JSON for live dashboard updates."""
    chart_type = request.GET.get('chart')
    params = _parse_date_params(request)
    date_from = date.fromisoformat(params['date_from'])
    date_to = date.fromisoformat(params['date_to'])

    chart_map = {
        'sales_trend': lambda: sales_trend_chart(date_from, date_to),
        'top_products': lambda: top_products_chart(date_from, date_to),
        'expenses': lambda: expense_by_category_chart(date_from, date_to),
        'monthly_profit': lambda: monthly_profit_chart(6),
        'payment_methods': lambda: payment_method_chart(date_from, date_to),
    }

    fn = chart_map.get(chart_type)
    if not fn:
        return JsonResponse({'error': 'Unknown chart type'}, status=400)

    return JsonResponse(fn())