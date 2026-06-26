from django.urls import path
from . import views, receipt_views

app_name = 'sales'

urlpatterns = [
    # ── POS Screen ────────────────────────────────────────────────────────────
    path('', views.pos_screen, name='pos'),

    # ── Product Search / Barcode ──────────────────────────────────────────────
    path('search/', views.product_search, name='product_search'),
    path('barcode/', views.barcode_lookup, name='barcode_lookup'),
    path('units/<int:product_pk>/', views.available_units, name='available_units'),

    # ── Cart Management ───────────────────────────────────────────────────────
    path('cart/', views.cart_state, name='cart_state'),
    path('cart/add/', views.cart_add, name='cart_add'),
    path('cart/update/', views.cart_update, name='cart_update'),
    path('cart/remove/', views.cart_remove, name='cart_remove'),
    path('cart/clear/', views.cart_clear, name='cart_clear'),
    path('cart/customer/', views.cart_set_customer, name='cart_set_customer'),

    # ── Discount ──────────────────────────────────────────────────────────────
    path('discount/apply/', views.apply_discount, name='apply_discount'),
    path('discount/remove/', views.remove_discount, name='remove_discount'),

    # ── Checkout ──────────────────────────────────────────────────────────────
    path('checkout/', views.checkout, name='checkout'),

    # ── Receipts ──────────────────────────────────────────────────────────────
    path('<int:pk>/receipt/', views.receipt, name='receipt'),
    path('<int:pk>/receipt/pdf/', receipt_views.download_receipt_pdf, name='receipt_pdf'),
    path('<int:pk>/receipt/thermal/', receipt_views.thermal_receipt, name='thermal_receipt'),
    path('item/<int:item_pk>/warranty/', receipt_views.download_warranty_card, name='warranty_card'),

    # ── Sale History ──────────────────────────────────────────────────────────
    path('history/', views.sale_list, name='sale_list'),
    path('history/<int:pk>/', views.sale_detail, name='sale_detail'),

    # ── Dashboard Stats (AJAX) ────────────────────────────────────────────────
    path('stats/', views.dashboard_stats, name='dashboard_stats'),
]