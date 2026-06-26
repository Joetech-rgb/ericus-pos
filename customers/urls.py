from django.urls import path
from . import views

app_name = 'customers'

urlpatterns = [
    # Main CRUD
    path('',                          views.customer_list,       name='list'),
    path('add/',                      views.customer_create,     name='create'),
    path('<int:pk>/',                 views.customer_detail,     name='detail'),
    path('<int:pk>/edit/',            views.customer_edit,       name='edit'),
    path('<int:pk>/deactivate/',      views.customer_deactivate, name='deactivate'),

    # Credit
    path('<int:pk>/credit-payment/',  views.record_credit_payment, name='credit_payment'),

    # AJAX — used by POS
    path('search/',                   views.customer_search_ajax,  name='search_ajax'),
    path('<int:pk>/info/',            views.customer_info_ajax,    name='info_ajax'),
]