from django.urls import path
from . import views

app_name = 'audit'

urlpatterns = [
    path('',          views.audit_log_list,   name='log_list'),
    path('<int:pk>/', views.audit_log_detail,  name='log_detail'),
    path('export/',   views.audit_export_csv,  name='export_csv'),
    path('clear/',    views.audit_clear,        name='clear'),
]