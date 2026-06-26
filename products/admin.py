from django.contrib import admin
from .models import Category, Product, ProductUnit


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display  = ['name', 'icon', 'product_count', 'is_active']
    list_filter   = ['is_active']
    search_fields = ['name']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display  = ['name', 'brand', 'category', 'selling_price',
                     'current_stock', 'is_low_stock', 'is_active']
    list_filter   = ['category', 'is_active', 'track_serials']
    search_fields = ['name', 'brand', 'model_number', 'barcode', 'sku']
    readonly_fields = ['created_at', 'updated_at', 'created_by']


@admin.register(ProductUnit)
class ProductUnitAdmin(admin.ModelAdmin):
    list_display  = ['product', 'serial_number', 'condition', 'status', 'received_at']
    list_filter   = ['status', 'condition']
    search_fields = ['serial_number', 'product__name']
    readonly_fields = ['received_at', 'sold_at', 'added_by']