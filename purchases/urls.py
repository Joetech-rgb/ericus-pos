from django.urls import path
from . import views

app_name = 'purchases'

urlpatterns = [
    # Purchase Orders
    path('', views.po_list, name='po_list'),
    path('create/', views.po_create, name='po_create'),
    path('<int:pk>/', views.po_detail, name='po_detail'),
    path('<int:pk>/edit/', views.po_edit, name='po_edit'),
    path('<int:pk>/mark-ordered/', views.po_mark_ordered, name='po_mark_ordered'),
    path('<int:pk>/cancel/', views.po_cancel, name='po_cancel'),
    path('<int:pk>/payment/', views.payment_update, name='payment_update'),

    # GRN
    path('<int:po_pk>/receive/', views.grn_create, name='grn_create'),

    # Suppliers
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/add/', views.supplier_create, name='supplier_create'),
    path('suppliers/<int:pk>/', views.supplier_detail, name='supplier_detail'),
    path('suppliers/<int:pk>/edit/', views.supplier_edit, name='supplier_edit'),

    # AJAX
    path('ajax/supplier-search/', views.supplier_search_ajax, name='supplier_search_ajax'),
]