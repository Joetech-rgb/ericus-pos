from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # Main dashboard
    path('', views.stock_dashboard, name='stock_dashboard'),

    # Per-product stock
    path('product/<int:product_pk>/', views.stock_detail, name='stock_detail'),
    path('product/<int:product_pk>/adjust/', views.stock_adjustment, name='stock_adjustment'),

    # Demo unit management
    path('demo/', views.demo_unit_list, name='demo_units'),
    path('demo/convert/<int:unit_pk>/', views.convert_to_demo, name='convert_to_demo'),
    path('demo/return/<int:demo_pk>/', views.return_demo, name='return_demo'),

    # Movement log (owner only)
    path('movements/', views.movement_log, name='movement_log'),

    # Stock audits
    path('audits/', views.audit_list, name='audit_list'),
    path('audits/new/', views.audit_create, name='audit_create'),
    path('audits/<int:pk>/', views.audit_detail, name='audit_detail'),
    path('audits/<int:pk>/update-item/<int:item_pk>/', views.audit_update_item, name='audit_update_item'),
    path('audits/<int:pk>/complete/', views.audit_complete, name='audit_complete'),
    path('audits/<int:pk>/cancel/', views.audit_cancel, name='audit_cancel'),
]