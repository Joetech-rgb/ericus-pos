from django.contrib import admin
from .models import Supplier, PurchaseOrder, PurchaseOrderItem, GoodsReceivedNote, GRNItem


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_person', 'phone', 'city', 'total_orders', 'is_active']
    list_filter = ['is_active', 'city']
    search_fields = ['name', 'contact_person', 'phone', 'email']
    list_editable = ['is_active']


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 0
    readonly_fields = ['line_total', 'quantity_received']


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = [
        'po_number', 'supplier', 'status', 'order_date',
        'grand_total', 'amount_paid', 'amount_due', 'created_by'
    ]
    list_filter = ['status', 'payment_method', 'order_date']
    search_fields = ['po_number', 'supplier__name']
    readonly_fields = ['po_number', 'subtotal', 'grand_total', 'created_by', 'approved_by', 'approved_at']
    inlines = [PurchaseOrderItemInline]
    date_hierarchy = 'order_date'

    def amount_due(self, obj):
        return obj.amount_due
    amount_due.short_description = 'Amount Due'


class GRNItemInline(admin.TabularInline):
    model = GRNItem
    extra = 0
    readonly_fields = ['po_item', 'quantity_received', 'condition']


@admin.register(GoodsReceivedNote)
class GRNAdmin(admin.ModelAdmin):
    list_display = ['grn_number', 'purchase_order', 'received_by', 'received_date', 'total_units_received']
    list_filter = ['received_date']
    search_fields = ['grn_number', 'purchase_order__po_number']
    readonly_fields = ['grn_number', 'received_by', 'created_at']
    inlines = [GRNItemInline]
    date_hierarchy = 'received_date'