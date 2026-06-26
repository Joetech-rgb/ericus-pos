from django.urls import path
from . import views

app_name = 'returns'

urlpatterns = [
    path('', views.return_list, name='return_list'),
    path('new/', views.return_create, name='return_create'),
    path('<int:pk>/', views.return_detail, name='return_detail'),
    path('<int:pk>/approve/', views.return_approve, name='return_approve'),
    path('<int:pk>/reject/', views.return_reject, name='return_reject'),
    path('<int:pk>/resolve/', views.return_resolve, name='return_resolve'),
    path('ajax/sale-items/', views.return_sale_items_ajax, name='sale_items_ajax'),
]