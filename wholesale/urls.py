from django.urls import path
from . import views

app_name = 'wholesale'

urlpatterns = [
    # Dashboard
    path('', views.wholesale_dashboard, name='dashboard'),

    # Order CRUD
    path('orders/', views.order_list, name='order_list'),
    path('orders/create/', views.order_create, name='order_create'),
    path('orders/<int:pk>/', views.order_detail, name='order_detail'),
    path('orders/<int:pk>/edit/', views.order_edit, name='order_edit'),

    # Order status transitions
    path('orders/<int:pk>/confirm/', views.order_confirm, name='order_confirm'),
    path('orders/<int:pk>/pack/', views.order_mark_packed, name='order_mark_packed'),
    path('orders/<int:pk>/deliver/', views.order_deliver, name='order_deliver'),
    path('orders/<int:pk>/cancel/', views.order_cancel, name='order_cancel'),

    # Payment
    path('orders/<int:pk>/payment/', views.order_payment, name='order_payment'),

    # AJAX
    path('ajax/product-price/', views.product_price_ajax, name='product_price_ajax'),
]