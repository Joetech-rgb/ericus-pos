import os

os.makedirs(os.path.join('templates', 'reports'), exist_ok=True)

dashboard = """\
{% extends "base.html" %}
{% block title %}Reports{% endblock %}
{% block page_title %}Reports Dashboard{% endblock %}
{% block nav_reports %}active{% endblock %}

{% block content %}
<div class="stats-row" style="margin-bottom:18px;">
  <div class="stat-box">
    <div class="s-label">Revenue This Month</div>
    <div class="s-value text-success">GHS {{ pl.total_revenue|default:"0.00" }}</div>
  </div>
  <div class="stat-box">
    <div class="s-label">Gross Profit</div>
    <div class="s-value" style="color:#4a6cf7;">GHS {{ pl.gross_profit|default:"0.00" }}</div>
  </div>
  <div class="stat-box">
    <div class="s-label">Total Expenses</div>
    <div class="s-value text-danger">GHS {{ pl.total_expenses|default:"0.00" }}</div>
  </div>
  <div class="stat-box">
    <div class="s-label">Net Profit</div>
    <div class="s-value" style="color:#28a745;">GHS {{ pl.net_profit|default:"0.00" }}</div>
  </div>
  <div class="stat-box">
    <div class="s-label">Low Stock Items</div>
    <div class="s-value text-danger">{{ inv.low_stock_count|default:"0" }}</div>
  </div>
</div>

<div class="grid-2" style="margin-bottom:18px;">
  <div class="card">
    <div class="card-head"><h3>Monthly Profit vs Expenses</h3></div>
    <div class="card-body">
      <canvas id="profitChart" height="200"></canvas>
    </div>
  </div>
  <div class="card">
    <div class="card-head"><h3>Payment Methods</h3></div>
    <div class="card-body">
      <canvas id="paymentChart" height="200"></canvas>
    </div>
  </div>
</div>

<div class="card">
  <div class="card-head"><h3>All Reports</h3></div>
  <div class="card-body">
    <div class="grid-3">
      <a href="/reports/sales/" class="stat-box" style="text-decoration:none;display:block;">
        <div class="s-label">Sales Summary</div>
        <div class="s-sub">Revenue, transactions, daily breakdown</div>
      </a>
      <a href="/reports/sales/by-product/" class="stat-box" style="text-decoration:none;display:block;">
        <div class="s-label">Sales by Product</div>
        <div class="s-sub">Top products, units sold, profit</div>
      </a>
      <a href="/reports/sales/by-attendant/" class="stat-box" style="text-decoration:none;display:block;">
        <div class="s-label">Sales by Attendant</div>
        <div class="s-sub">Staff performance breakdown</div>
      </a>
      <a href="/reports/inventory/" class="stat-box" style="text-decoration:none;display:block;">
        <div class="s-label">Inventory Status</div>
        <div class="s-sub">Stock levels, low stock alerts</div>
      </a>
      <a href="/reports/expenses/" class="stat-box" style="text-decoration:none;display:block;">
        <div class="s-label">Expense Summary</div>
        <div class="s-sub">Expenses by category</div>
      </a>
      <a href="/reports/profit-loss/" class="stat-box" style="text-decoration:none;display:block;">
        <div class="s-label">Profit & Loss</div>
        <div class="s-sub">Full P&L statement</div>
      </a>
      <a href="/reports/purchases/" class="stat-box" style="text-decoration:none;display:block;">
        <div class="s-label">Purchase Summary</div>
        <div class="s-sub">Supplier purchases overview</div>
      </a>
      <a href="/reports/customers/credit/" class="stat-box" style="text-decoration:none;display:block;">
        <div class="s-label">Customer Credit</div>
        <div class="s-sub">Outstanding balances</div>
      </a>
      <a href="/reports/returns/" class="stat-box" style="text-decoration:none;display:block;">
        <div class="s-label">Returns Summary</div>
        <div class="s-sub">Product returns and refunds</div>
      </a>
      <a href="/reports/attendants/" class="stat-box" style="text-decoration:none;display:block;">
        <div class="s-label">Attendant Performance</div>
        <div class="s-sub">Staff metrics and rankings</div>
      </a>
    </div>
  </div>
</div>

{% endblock %}

{% block extra_js %}
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
const profitData = {{ profit_chart_json|safe }};
const paymentData = {{ payment_chart_json|safe }};
new Chart(document.getElementById('profitChart'), profitData);
new Chart(document.getElementById('paymentChart'), paymentData);
</script>
{% endblock %}
"""

with open(os.path.join('templates', 'reports', 'dashboard.html'), 'w', encoding='utf-8') as f:
    f.write(dashboard)
print('reports/dashboard.html written OK')
