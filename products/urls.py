from django.urls import path
from . import views

urlpatterns = [
    # Products
    path('',                                views.product_list,       name='product_list'),
    path('create/',                         views.product_create,     name='product_create'),
    path('<int:product_id>/',               views.product_detail,     name='product_detail'),
    path('<int:product_id>/edit/',          views.product_edit,       name='product_edit'),
    path('<int:product_id>/deactivate/',    views.product_deactivate, name='product_deactivate'),
    path('<int:product_id>/add-unit/',      views.add_unit,           name='add_unit'),

    # Units
    path('units/<int:unit_id>/demo/',       views.convert_to_demo,     name='convert_to_demo'),
    path('units/<int:unit_id>/sellable/',   views.convert_to_sellable, name='convert_to_sellable'),

    # Categories
    path('categories/',                     views.category_list,   name='category_list'),
    path('categories/create/',              views.category_create, name='category_create'),
    path('categories/<int:category_id>/edit/', views.category_edit, name='category_edit'),

    # AJAX
    path('search/',                         views.product_search,  name='product_search'),
    path('barcode/',                        views.barcode_lookup,  name='barcode_lookup'),

    # Bulk Import
    path('import/',                         views.bulk_import,     name='bulk_import'),
]