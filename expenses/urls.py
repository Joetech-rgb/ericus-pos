from django.urls import path
from . import views

app_name = 'expenses'

urlpatterns = [
    # Expenses
    path('',                      views.expense_list,     name='list'),
    path('add/',                  views.expense_create,   name='create'),
    path('<int:pk>/edit/',        views.expense_edit,     name='edit'),
    path('<int:pk>/approve/',     views.expense_approve,  name='approve'),
    path('<int:pk>/reject/',      views.expense_reject,   name='reject'),
    path('<int:pk>/delete/',      views.expense_delete,   name='delete'),

    # Categories
    path('categories/',           views.category_list,    name='category_list'),
    path('categories/add/',       views.category_create,  name='category_create'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
]