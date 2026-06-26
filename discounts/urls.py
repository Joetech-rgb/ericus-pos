from django.urls import path
from . import views

app_name = 'discounts'

urlpatterns = [
    path('',                  views.discount_list,    name='list'),
    path('create/',           views.discount_create,  name='create'),
    path('<int:pk>/edit/',    views.discount_edit,    name='edit'),
    path('<int:pk>/toggle/',  views.discount_toggle,  name='toggle'),
    path('<int:pk>/delete/',  views.discount_delete,  name='delete'),
    path('<int:pk>/usage/',   views.discount_usage,   name='usage'),

    # AJAX — POS promo code validation
    path('validate/',         views.validate_code_ajax, name='validate_ajax'),
]