from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('',                    views.reports_dashboard,     name='dashboard'),
    path('sales/',              views.sales_summary,         name='sales_summary'),
    path('sales/by-product/',   views.sales_by_product,      name='sales_by_product'),
    path('sales/by-attendant/', views.sales_by_attendant,    name='sales_by_attendant'),
    path('inventory/',          views.inventory_status,       name='inventory_status'),
    path('expenses/',           views.expense_summary,        name='expense_summary'),
    path('profit-loss/',        views.profit_loss,            name='profit_loss'),
    path('purchases/',          views.purchase_summary,       name='purchase_summary'),
    path('customers/credit/',   views.customer_credit,        name='customer_credit'),
    path('returns/',            views.returns_summary,        name='returns_summary'),
    path('attendants/',         views.attendant_performance,  name='attendant_performance'),
    path('charts/ajax/',        views.chart_data_ajax,        name='chart_data_ajax'),
]