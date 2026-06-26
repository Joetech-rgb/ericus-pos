import os

list_html = """\
{% extends "base.html" %}
{% block title %}Audit and Logs{% endblock %}
{% block page_title %}Audit & Logs{% endblock %}
{% block nav_audit %}active{% endblock %}
{% block topbar_actions %}
<a href="{% url 'audit:export_csv' %}?{{ request.GET.urlencode }}" class="btn btn-success btn-sm">Export CSV</a>
<form method="post" action="{% url 'audit:clear' %}" style="display:inline" onsubmit="return confirm('Delete logs older than 90 days?')">{% csrf_token %}<button type="submit" class="btn btn-danger btn-sm">Purge Old</button></form>
{% endblock %}
{% block content %}
<div class="stats-row" style="grid-template-columns:repeat(3,1fr);margin-bottom:18px;">
  <div class="stat-box"><div class="s-label">Events Today</div><div class="s-value" style="color:#4a6cf7;">{{ total_today }}</div></div>
  <div class="stat-box"><div class="s-label">Warnings Today</div><div class="s-value" style="color:#ffc107;">{{ total_warnings }}</div></div>
  <div class="stat-box"><div class="s-label">Critical All Time</div><div class="s-value" style="color:#dc3545;">{{ total_critical }}</div></div>
</div>
<div class="card" style="margin-bottom:14px;">
  <div class="card-body">
    <form method="get" class="filter-bar">
      <input type="text" name="q" class="form-control" style="max-width:200px;" placeholder="Search..." value="{{ filters.q }}">
      <select name="category" class="form-control" style="max-width:150px;"><option value="">All Categories</option>{% for val, label in categories %}<option value="{{ val }}" {% if filters.category == val %}selected{% endif %}>{{ label }}</option>{% endfor %}</select>
      <select name="level" class="form-control" style="max-width:120px;"><option value="">All Levels</option>{% for val, label in levels %}<option value="{{ val }}" {% if filters.level == val %}selected{% endif %}>{{ label }}</option>{% endfor %}</select>
      <input type="text" name="user" class="form-control" style="max-width:130px;" placeholder="Username" value="{{ filters.user }}">
      <input type="date" name="date_from" class="form-control" style="max-width:140px;" value="{{ filters.date_from }}">
      <input type="date" name="date_to" class="form-control" style="max-width:140px;" value="{{ filters.date_to }}">
      <button type="submit" class="btn btn-primary btn-sm">Filter</button>
      <a href="{% url 'audit:log_list' %}" class="btn btn-outline btn-sm">Clear</a>
    </form>
    <div class="flex gap-2 mt-2">
      <span class="text-muted text-sm">Quick:</span>
      <a href="?quick=today" class="btn btn-sm btn-outline {% if filters.quick == 'today' %}btn-primary{% endif %}">Today</a>
      <a href="?quick=week" class="btn btn-sm btn-outline {% if filters.quick == 'week' %}btn-primary{% endif %}">Last 7 Days</a>
      <a href="?quick=month" class="btn btn-sm btn-outline {% if filters.quick == 'month' %}btn-primary{% endif %}">Last 30 Days</a>
      <a href="?quick=critical" class="btn btn-sm btn-outline {% if filters.quick == 'critical' %}btn-danger{% endif %}" style="color:#dc3545;">Critical Only</a>
    </div>
  </div>
</div>
<div class="card">
  <div class="card-head"><h3>Log Entries</h3><span class="text-muted text-sm">{{ page_obj.paginator.count }} total</span></div>
  <div class="table-wrap">
    <table>
      <thead><tr><th>Timestamp</th><th>Level</th><th>Category</th><th>User</th><th>Action</th><th>Object</th><th>IP</th><th></th></tr></thead>
      <tbody>
        {% for log in page_obj %}
        <tr>
          <td class="text-sm text-muted" style="white-space:nowrap;">{{ log.timestamp|date:"Y-m-d H:i" }}</td>
          <td>{% if log.level == 'critical' %}<span class="badge badge-danger">Critical</span>{% elif log.level == 'warning' %}<span class="badge badge-warning">Warning</span>{% else %}<span class="badge badge-info">Info</span>{% endif %}</td>
          <td class="text-sm">{{ log.get_category_display }}</td>
          <td class="text-sm">{{ log.username|default:"System" }}{% if log.user_role %} <span class="text-muted">({{ log.user_role }})</span>{% endif %}</td>
          <td class="text-sm">{{ log.action }}</td>
          <td class="text-sm text-muted" style="max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{% if log.object_type %}{{ log.object_type }}{% if log.object_id %} #{{ log.object_id }}{% endif %}{% endif %}</td>
          <td class="text-sm text-muted">{{ log.ip_address|default:"&mdash;" }}</td>
          <td><a href="{% url 'audit:log_detail' log.pk %}" class="btn btn-outline btn-sm">View</a></td>
        </tr>
        {% empty %}<tr><td colspan="8" class="text-center text-muted" style="padding:40px;">No audit entries found.</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  {% if page_obj.has_other_pages %}
  <div class="pagination">
    {% if page_obj.has_previous %}<a class="page-link" href="?{{ request.GET.urlencode }}&page={{ page_obj.previous_page_number }}">&laquo;</a>{% endif %}
    {% for num in page_obj.paginator.page_range %}{% if num == page_obj.number %}<span class="page-link active">{{ num }}</span>{% elif num >= page_obj.number|add:"-2" and num <= page_obj.number|add:"2" %}<a class="page-link" href="?{{ request.GET.urlencode }}&page={{ num }}">{{ num }}</a>{% endif %}{% endfor %}
    {% if page_obj.has_next %}<a class="page-link" href="?{{ request.GET.urlencode }}&page={{ page_obj.next_page_number }}">&raquo;</a>{% endif %}
    <span class="text-muted text-sm" style="margin-left:8px;">Page {{ page_obj.number }} of {{ page_obj.paginator.num_pages }}</span>
  </div>
  {% endif %}
</div>
{% endblock %}
"""

with open(os.path.join('templates', 'audit', 'audit_log_list.html'), 'w', encoding='utf-8') as f:
    f.write(list_html)

print('audit_log_list.html written OK')
