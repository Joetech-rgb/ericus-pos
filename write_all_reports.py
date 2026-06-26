import os

BASE = os.path.join('templates', 'reports')
os.makedirs(BASE, exist_ok=True)

templates = {}

# ── Sales Summary ─────────────────────────────────────────────────
templates['sales_summary.html'] = """\
{% extends "base.html" %}
{% block title %}Sales Summary{% endblock %}
{% block page_title %}Sales Summary{% endblock %}
{% block nav_reports %}active{% endblock %}
{% block topbar_actions %}
<a href="/reports/" class="btn btn-outline btn-sm">&larr; Reports</a>
<a href="?date_from={{ date_from }}&date_to={{ date_to }}&format=csv" class="btn btn-success btn-sm">Export CSV</a>
<a href="?date_from={{ date_from }}&date_to={{ date_to }}&format=pdf" class="btn btn-danger btn-sm">Export PDF</a>
{% endblock %}
{% block content %}
<form method="get" class="filter-bar" style="margin-bottom:14px;">
  <input type="date" name="date_from" class="form-control" style="max-width:160px;" value="{{ date_from }}">
  <input type="date" name="date_to" class="form-control" style="max-width:160px;" value="{{ date_to }}">
  <button type="submit" class="btn btn-primary btn-sm">Filter</button>
</form>
<div class="stats-row" style="margin-bottom:18px;">
  <div class="stat-box"><div class="s-label">Transactions</div><div class="s-value">{{ data.total_transactions }}</div></div>
  <div class="stat-box"><div class="s-label">Gross Revenue</div><div class="s-value text-success">GHS {{ data.gross_revenue|floatformat:2 }}</div></div>
  <div class="stat-box"><div class="s-label">Total Discounts</div><div class="s-value text-danger">GHS {{ data.total_discounts|floatformat:2 }}</div></div>
  <div class="stat-box"><div class="s-label">Gross Profit</div><div class="s-value" style="color:#4a6cf7;">GHS {{ data.gross_profit|floatformat:2 }}</div></div>
</div>
<div class="grid-2" style="margin-bottom:18px;">
  <div class="card"><div class="card-head"><h3>Sales Trend</h3></div><div class="card-body"><canvas id="trendChart" height="220"></canvas></div></div>
  <div class="card"><div class="card-head"><h3>Top Products</h3></div><div class="card-body"><canvas id="topChart" height="220"></canvas></div></div>
</div>
<div class="card">
  <div class="card-head"><h3>Daily Breakdown</h3></div>
  <div class="table-wrap">
    <table>
      <thead><tr><th>Date</th><th>Transactions</th><th class="text-right">Revenue (GHS)</th></tr></thead>
      <tbody>
        {% for row in data.daily_breakdown %}
        <tr>
          <td class="text-sm">{{ row.created_at__date }}</td>
          <td class="text-sm">{{ row.count }}</td>
          <td class="text-sm text-right">{{ row.revenue|floatformat:2 }}</td>
        </tr>
        {% empty %}<tr><td colspan="3" class="text-center text-muted" style="padding:30px;">No sales in this period.</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
{% block extra_js %}
{% load static %}
<script src="{% static 'js/chart.min.js' %}"></script>
<script>
new Chart(document.getElementById('trendChart'), {{ trend_chart_json|safe }});
new Chart(document.getElementById('topChart'), {{ top_chart_json|safe }});
</script>
{% endblock %}
"""

# ── Sales by Product ──────────────────────────────────────────────
templates['sales_by_product.html'] = """\
{% extends "base.html" %}
{% block title %}Sales by Product{% endblock %}
{% block page_title %}Sales by Product{% endblock %}
{% block nav_reports %}active{% endblock %}
{% block topbar_actions %}
<a href="/reports/" class="btn btn-outline btn-sm">&larr; Reports</a>
<a href="?date_from={{ date_from }}&date_to={{ date_to }}&format=csv" class="btn btn-success btn-sm">Export CSV</a>
{% endblock %}
{% block content %}
<form method="get" class="filter-bar" style="margin-bottom:14px;">
  <input type="date" name="date_from" class="form-control" style="max-width:160px;" value="{{ date_from }}">
  <input type="date" name="date_to" class="form-control" style="max-width:160px;" value="{{ date_to }}">
  <button type="submit" class="btn btn-primary btn-sm">Filter</button>
</form>
<div class="stats-row" style="margin-bottom:18px;">
  <div class="stat-box"><div class="s-label">Total Revenue</div><div class="s-value text-success">GHS {{ data.grand_total_revenue|floatformat:2 }}</div></div>
  <div class="stat-box"><div class="s-label">Total Profit</div><div class="s-value" style="color:#4a6cf7;">GHS {{ data.grand_total_profit|floatformat:2 }}</div></div>
</div>
<div class="card">
  <div class="card-head"><h3>Product Performance</h3></div>
  <div class="table-wrap">
    <table>
      <thead><tr><th>Product</th><th>Brand</th><th>Units Sold</th><th class="text-right">Revenue (GHS)</th><th class="text-right">COGS (GHS)</th><th class="text-right">Profit (GHS)</th></tr></thead>
      <tbody>
        {% for row in data.rows %}
        <tr>
          <td class="text-sm">{{ row.product_name_at_sale }}</td>
          <td class="text-sm text-muted">{{ row.product_brand_at_sale }}</td>
          <td class="text-sm">{{ row.units_sold }}</td>
          <td class="text-sm text-right">{{ row.total_revenue|floatformat:2 }}</td>
          <td class="text-sm text-right">{{ row.total_cost|floatformat:2 }}</td>
          <td class="text-sm text-right {% if row.gross_profit > 0 %}text-success{% else %}text-danger{% endif %}">{{ row.gross_profit|floatformat:2 }}</td>
        </tr>
        {% empty %}<tr><td colspan="6" class="text-center text-muted" style="padding:30px;">No data.</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
"""

# ── Sales by Attendant ────────────────────────────────────────────
templates['sales_by_attendant.html'] = """\
{% extends "base.html" %}
{% block title %}Sales by Attendant{% endblock %}
{% block page_title %}Sales by Attendant{% endblock %}
{% block nav_reports %}active{% endblock %}
{% block topbar_actions %}
<a href="/reports/" class="btn btn-outline btn-sm">&larr; Reports</a>
{% endblock %}
{% block content %}
<form method="get" class="filter-bar" style="margin-bottom:14px;">
  <input type="date" name="date_from" class="form-control" style="max-width:160px;" value="{{ date_from }}">
  <input type="date" name="date_to" class="form-control" style="max-width:160px;" value="{{ date_to }}">
  <button type="submit" class="btn btn-primary btn-sm">Filter</button>
</form>
<div class="card">
  <div class="card-head"><h3>Attendant Performance</h3></div>
  <div class="table-wrap">
    <table>
      <thead><tr><th>Attendant</th><th>Transactions</th><th class="text-right">Revenue (GHS)</th><th class="text-right">Discounts (GHS)</th></tr></thead>
      <tbody>
        {% for row in data.rows %}
        <tr>
          <td class="text-sm">{{ row.attendant__first_name }} {{ row.attendant__last_name }}<span class="text-muted"> ({{ row.attendant__username }})</span></td>
          <td class="text-sm">{{ row.transaction_count }}</td>
          <td class="text-sm text-right">{{ row.total_revenue|floatformat:2 }}</td>
          <td class="text-sm text-right text-danger">{{ row.total_discounts|floatformat:2 }}</td>
        </tr>
        {% empty %}<tr><td colspan="4" class="text-center text-muted" style="padding:30px;">No data.</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
"""

# ── Inventory Status ──────────────────────────────────────────────
templates['inventory_status.html'] = """\
{% extends "base.html" %}
{% block title %}Inventory Status{% endblock %}
{% block page_title %}Inventory Status{% endblock %}
{% block nav_reports %}active{% endblock %}
{% block topbar_actions %}
<a href="/reports/" class="btn btn-outline btn-sm">&larr; Reports</a>
<a href="?format=csv" class="btn btn-success btn-sm">Export CSV</a>
<a href="?format=pdf" class="btn btn-danger btn-sm">Export PDF</a>
{% endblock %}
{% block content %}
<form method="get" class="filter-bar" style="margin-bottom:14px;">
  <select name="category_id" class="form-control" style="max-width:180px;">
    <option value="">All Categories</option>
    {% for cat in categories %}<option value="{{ cat.id }}" {% if selected_category == cat.id|stringformat:"s" %}selected{% endif %}>{{ cat.name }}</option>{% endfor %}
  </select>
  <label style="display:flex;align-items:center;gap:6px;font-size:13px;">
    <input type="checkbox" name="low_stock_only" value="1" {% if low_stock_only %}checked{% endif %}> Low Stock Only
  </label>
  <button type="submit" class="btn btn-primary btn-sm">Filter</button>
</form>
<div class="stats-row" style="margin-bottom:18px;">
  <div class="stat-box"><div class="s-label">Total Stock Value</div><div class="s-value" style="color:#4a6cf7;">GHS {{ data.total_value|floatformat:2 }}</div></div>
  <div class="stat-box"><div class="s-label">Low Stock Items</div><div class="s-value text-danger">{{ data.low_stock_count }}</div></div>
  <div class="stat-box"><div class="s-label">Total Products</div><div class="s-value">{{ data.rows|length }}</div></div>
</div>
<div class="card">
  <div class="card-head"><h3>Stock Levels</h3></div>
  <div class="table-wrap">
    <table>
      <thead><tr><th>Product</th><th>Category</th><th>In Stock</th><th>Reorder Point</th><th>Status</th><th class="text-right">Stock Value (GHS)</th></tr></thead>
      <tbody>
        {% for row in data.rows %}
        <tr>
          <td class="text-sm">{{ row.product.name }}</td>
          <td class="text-sm text-muted">{{ row.product.category.name|default:"&mdash;" }}</td>
          <td class="text-sm {% if row.is_low %}text-danger text-bold{% endif %}">{{ row.current_qty }}</td>
          <td class="text-sm text-muted">{{ row.reorder_point }}</td>
          <td><span class="badge {% if row.is_low %}badge-danger{% else %}badge-success{% endif %}">{% if row.is_low %}Low{% else %}OK{% endif %}</span></td>
          <td class="text-sm text-right">{{ row.stock_value|floatformat:2 }}</td>
        </tr>
        {% empty %}<tr><td colspan="6" class="text-center text-muted" style="padding:30px;">No products found.</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
"""

# ── Expense Summary ───────────────────────────────────────────────
templates['expense_summary.html'] = """\
{% extends "base.html" %}
{% block title %}Expense Summary{% endblock %}
{% block page_title %}Expense Summary{% endblock %}
{% block nav_reports %}active{% endblock %}
{% block topbar_actions %}
<a href="/reports/" class="btn btn-outline btn-sm">&larr; Reports</a>
<a href="?date_from={{ date_from }}&date_to={{ date_to }}&format=csv" class="btn btn-success btn-sm">Export CSV</a>
{% endblock %}
{% block content %}
<form method="get" class="filter-bar" style="margin-bottom:14px;">
  <input type="date" name="date_from" class="form-control" style="max-width:160px;" value="{{ date_from }}">
  <input type="date" name="date_to" class="form-control" style="max-width:160px;" value="{{ date_to }}">
  <button type="submit" class="btn btn-primary btn-sm">Filter</button>
</form>
<div class="stats-row" style="margin-bottom:18px;">
  <div class="stat-box"><div class="s-label">Total Expenses</div><div class="s-value text-danger">GHS {{ data.total_amount|floatformat:2 }}</div></div>
  <div class="stat-box"><div class="s-label">Total Records</div><div class="s-value">{{ data.total_count }}</div></div>
</div>
<div class="grid-2">
  <div class="card">
    <div class="card-head"><h3>By Category</h3></div>
    <div class="card-body"><canvas id="expChart" height="250"></canvas></div>
  </div>
  <div class="card">
    <div class="card-head"><h3>Category Breakdown</h3></div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Category</th><th>Count</th><th class="text-right">Total (GHS)</th></tr></thead>
        <tbody>
          {% for row in data.by_category %}
          <tr>
            <td class="text-sm">{{ row.category__name|default:"Uncategorised" }}</td>
            <td class="text-sm">{{ row.count }}</td>
            <td class="text-sm text-right">{{ row.total|floatformat:2 }}</td>
          </tr>
          {% empty %}<tr><td colspan="3" class="text-center text-muted" style="padding:20px;">No data.</td></tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>
</div>
{% endblock %}
{% block extra_js %}
{% load static %}
<script src="{% static 'js/chart.min.js' %}"></script>
<script>new Chart(document.getElementById('expChart'), {{ exp_chart_json|safe }});</script>
{% endblock %}
"""

# ── Profit & Loss ─────────────────────────────────────────────────
templates['profit_loss.html'] = """\
{% extends "base.html" %}
{% block title %}Profit & Loss{% endblock %}
{% block page_title %}Profit & Loss Statement{% endblock %}
{% block nav_reports %}active{% endblock %}
{% block topbar_actions %}
<a href="/reports/" class="btn btn-outline btn-sm">&larr; Reports</a>
<a href="?date_from={{ date_from }}&date_to={{ date_to }}&format=pdf" class="btn btn-danger btn-sm">Export PDF</a>
{% endblock %}
{% block content %}
<form method="get" class="filter-bar" style="margin-bottom:14px;">
  <input type="date" name="date_from" class="form-control" style="max-width:160px;" value="{{ date_from }}">
  <input type="date" name="date_to" class="form-control" style="max-width:160px;" value="{{ date_to }}">
  <button type="submit" class="btn btn-primary btn-sm">Filter</button>
</form>
<div style="max-width:600px;">
  <div class="card">
    <div class="card-head"><h3>P&L: {{ date_from }} to {{ date_to }}</h3></div>
    <div class="card-body">
      <table style="width:100%;border-collapse:collapse;">
        <tbody>
          <tr><td style="padding:10px 0;border-bottom:1px solid var(--border);" class="text-bold">Revenue</td><td class="text-right text-bold" style="padding:10px 0;border-bottom:1px solid var(--border);">GHS {{ data.revenue|floatformat:2 }}</td></tr>
          <tr><td style="padding:8px 0 8px 16px;border-bottom:1px solid var(--border);" class="text-sm text-muted">Less: Discounts Given</td><td class="text-right text-sm text-danger" style="padding:8px 0;border-bottom:1px solid var(--border);">({{ data.discounts_given|floatformat:2 }})</td></tr>
          <tr><td style="padding:10px 0;border-bottom:2px solid var(--border);" class="text-bold">Net Revenue</td><td class="text-right text-bold" style="padding:10px 0;border-bottom:2px solid var(--border);">GHS {{ data.net_revenue|floatformat:2 }}</td></tr>
          <tr><td style="padding:8px 0 8px 16px;border-bottom:1px solid var(--border);" class="text-sm text-muted">Less: Cost of Goods Sold</td><td class="text-right text-sm text-danger" style="padding:8px 0;border-bottom:1px solid var(--border);">({{ data.cogs|floatformat:2 }})</td></tr>
          <tr style="background:rgba(74,108,247,0.05);"><td style="padding:10px 0;border-bottom:2px solid var(--border);" class="text-bold">Gross Profit <span class="text-muted text-sm">({{ data.gross_margin_pct }}%)</span></td><td class="text-right text-bold {% if data.gross_profit > 0 %}text-success{% else %}text-danger{% endif %}" style="padding:10px 0;border-bottom:2px solid var(--border);">GHS {{ data.gross_profit|floatformat:2 }}</td></tr>
          <tr><td style="padding:8px 0 8px 16px;border-bottom:1px solid var(--border);" class="text-sm text-muted">Less: Operating Expenses</td><td class="text-right text-sm text-danger" style="padding:8px 0;border-bottom:1px solid var(--border);">({{ data.operating_expenses|floatformat:2 }})</td></tr>
          <tr style="background:rgba(40,167,69,0.07);"><td style="padding:12px 0;" class="text-bold" style="font-size:15px;">Net Profit <span class="text-muted text-sm">({{ data.net_margin_pct }}%)</span></td><td class="text-right text-bold {% if data.net_profit > 0 %}text-success{% else %}text-danger{% endif %}" style="padding:12px 0;font-size:15px;">GHS {{ data.net_profit|floatformat:2 }}</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</div>
{% endblock %}
"""

# ── Purchase Summary ──────────────────────────────────────────────
templates['purchase_summary.html'] = """\
{% extends "base.html" %}
{% block title %}Purchase Summary{% endblock %}
{% block page_title %}Purchase Summary{% endblock %}
{% block nav_reports %}active{% endblock %}
{% block topbar_actions %}
<a href="/reports/" class="btn btn-outline btn-sm">&larr; Reports</a>
{% endblock %}
{% block content %}
<form method="get" class="filter-bar" style="margin-bottom:14px;">
  <input type="date" name="date_from" class="form-control" style="max-width:160px;" value="{{ date_from }}">
  <input type="date" name="date_to" class="form-control" style="max-width:160px;" value="{{ date_to }}">
  <button type="submit" class="btn btn-primary btn-sm">Filter</button>
</form>
<div class="stats-row" style="margin-bottom:18px;">
  <div class="stat-box"><div class="s-label">Total Orders</div><div class="s-value">{{ data.total_orders }}</div></div>
  <div class="stat-box"><div class="s-label">Total Value</div><div class="s-value" style="color:#4a6cf7;">GHS {{ data.total_value|floatformat:2 }}</div></div>
  <div class="stat-box"><div class="s-label">Total Paid</div><div class="s-value text-success">GHS {{ data.total_paid|floatformat:2 }}</div></div>
  <div class="stat-box"><div class="s-label">Outstanding</div><div class="s-value text-danger">GHS {{ data.total_outstanding|floatformat:2 }}</div></div>
</div>
<div class="grid-2">
  <div class="card">
    <div class="card-head"><h3>By Supplier</h3></div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Supplier</th><th>Orders</th><th class="text-right">Value (GHS)</th></tr></thead>
        <tbody>
          {% for row in data.by_supplier %}
          <tr><td class="text-sm">{{ row.supplier__name }}</td><td class="text-sm">{{ row.order_count }}</td><td class="text-sm text-right">{{ row.total_value|floatformat:2 }}</td></tr>
          {% empty %}<tr><td colspan="3" class="text-center text-muted" style="padding:20px;">No data.</td></tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>
  <div class="card">
    <div class="card-head"><h3>By Status</h3></div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Status</th><th>Count</th><th class="text-right">Value (GHS)</th></tr></thead>
        <tbody>
          {% for row in data.by_status %}
          <tr><td class="text-sm">{{ row.status }}</td><td class="text-sm">{{ row.count }}</td><td class="text-sm text-right">{{ row.total|floatformat:2 }}</td></tr>
          {% empty %}<tr><td colspan="3" class="text-center text-muted" style="padding:20px;">No data.</td></tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>
</div>
{% endblock %}
"""

# ── Customer Credit ───────────────────────────────────────────────
templates['customer_credit.html'] = """\
{% extends "base.html" %}
{% block title %}Customer Credit{% endblock %}
{% block page_title %}Customer Credit Report{% endblock %}
{% block nav_reports %}active{% endblock %}
{% block topbar_actions %}
<a href="/reports/" class="btn btn-outline btn-sm">&larr; Reports</a>
<a href="?format=csv" class="btn btn-success btn-sm">Export CSV</a>
{% endblock %}
{% block content %}
<div class="stats-row" style="margin-bottom:18px;">
  <div class="stat-box"><div class="s-label">Customers with Credit</div><div class="s-value">{{ data.total_customers_with_credit }}</div></div>
  <div class="stat-box"><div class="s-label">Total Outstanding</div><div class="s-value text-danger">GHS {{ data.total_outstanding|floatformat:2 }}</div></div>
</div>
<div class="card">
  <div class="card-head"><h3>Credit Balances</h3></div>
  <div class="table-wrap">
    <table>
      <thead><tr><th>Name</th><th>Phone</th><th>Type</th><th class="text-right">Credit Balance (GHS)</th><th class="text-right">Credit Limit (GHS)</th></tr></thead>
      <tbody>
        {% for c in data.customers %}
        <tr>
          <td class="text-sm">{{ c.name }}</td>
          <td class="text-sm text-muted">{{ c.phone }}</td>
          <td class="text-sm"><span class="badge badge-primary">{{ c.customer_type }}</span></td>
          <td class="text-sm text-right text-danger">{{ c.credit_balance|floatformat:2 }}</td>
          <td class="text-sm text-right text-muted">{{ c.credit_limit|floatformat:2 }}</td>
        </tr>
        {% empty %}<tr><td colspan="5" class="text-center text-muted" style="padding:30px;">No customers with outstanding credit.</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
"""

# ── Returns Summary ───────────────────────────────────────────────
templates['returns_summary.html'] = """\
{% extends "base.html" %}
{% block title %}Returns Summary{% endblock %}
{% block page_title %}Returns Summary{% endblock %}
{% block nav_reports %}active{% endblock %}
{% block topbar_actions %}
<a href="/reports/" class="btn btn-outline btn-sm">&larr; Reports</a>
{% endblock %}
{% block content %}
<form method="get" class="filter-bar" style="margin-bottom:14px;">
  <input type="date" name="date_from" class="form-control" style="max-width:160px;" value="{{ date_from }}">
  <input type="date" name="date_to" class="form-control" style="max-width:160px;" value="{{ date_to }}">
  <button type="submit" class="btn btn-primary btn-sm">Filter</button>
</form>
<div class="stats-row" style="margin-bottom:18px;">
  <div class="stat-box"><div class="s-label">Total Returns</div><div class="s-value">{{ data.total_count }}</div></div>
  <div class="stat-box"><div class="s-label">Total Refunded</div><div class="s-value text-danger">GHS {{ data.total_refunded|floatformat:2 }}</div></div>
</div>
<div class="grid-2">
  <div class="card">
    <div class="card-head"><h3>By Reason</h3></div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Reason</th><th>Count</th><th class="text-right">Refunded (GHS)</th></tr></thead>
        <tbody>
          {% for row in data.by_reason %}
          <tr><td class="text-sm">{{ row.reason }}</td><td class="text-sm">{{ row.count }}</td><td class="text-sm text-right">{{ row.total_refunded|floatformat:2 }}</td></tr>
          {% empty %}<tr><td colspan="3" class="text-center text-muted" style="padding:20px;">No data.</td></tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>
  <div class="card">
    <div class="card-head"><h3>By Resolution</h3></div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Resolution</th><th>Count</th></tr></thead>
        <tbody>
          {% for row in data.by_resolution %}
          <tr><td class="text-sm">{{ row.resolution }}</td><td class="text-sm">{{ row.count }}</td></tr>
          {% empty %}<tr><td colspan="2" class="text-center text-muted" style="padding:20px;">No data.</td></tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>
</div>
{% endblock %}
"""

# ── Attendant Performance ─────────────────────────────────────────
templates['attendant_performance.html'] = """\
{% extends "base.html" %}
{% block title %}Attendant Performance{% endblock %}
{% block page_title %}Attendant Performance{% endblock %}
{% block nav_reports %}active{% endblock %}
{% block topbar_actions %}
<a href="/reports/" class="btn btn-outline btn-sm">&larr; Reports</a>
{% endblock %}
{% block content %}
<form method="get" class="filter-bar" style="margin-bottom:14px;">
  <input type="date" name="date_from" class="form-control" style="max-width:160px;" value="{{ date_from }}">
  <input type="date" name="date_to" class="form-control" style="max-width:160px;" value="{{ date_to }}">
  <button type="submit" class="btn btn-primary btn-sm">Filter</button>
</form>
<div class="card">
  <div class="card-head"><h3>Staff Performance: {{ date_from }} to {{ date_to }}</h3></div>
  <div class="table-wrap">
    <table>
      <thead><tr><th>Attendant</th><th>Sales</th><th class="text-right">Revenue (GHS)</th><th class="text-right">Discounts (GHS)</th><th class="text-right">Avg Sale (GHS)</th></tr></thead>
      <tbody>
        {% for row in data.rows %}
        <tr>
          <td class="text-sm">{{ row.attendant__first_name }} {{ row.attendant__last_name }} <span class="text-muted">({{ row.attendant__username }})</span></td>
          <td class="text-sm">{{ row.total_sales }}</td>
          <td class="text-sm text-right text-success">{{ row.total_revenue|floatformat:2 }}</td>
          <td class="text-sm text-right text-danger">{{ row.total_discounts|floatformat:2 }}</td>
          <td class="text-sm text-right">{{ row.avg_sale_value|floatformat:2 }}</td>
        </tr>
        {% empty %}<tr><td colspan="5" class="text-center text-muted" style="padding:30px;">No data.</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
"""

for filename, content in templates.items():
    path = os.path.join(BASE, filename)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Written: {filename}")

print("\nAll report templates done!")
