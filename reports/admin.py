from django.contrib import admin
from .models import SavedReport


@admin.register(SavedReport)
class SavedReportAdmin(admin.ModelAdmin):
    list_display = ['name', 'report_type', 'format', 'generated_by', 'created_at']
    list_filter = ['report_type', 'format', 'created_at']
    search_fields = ['name', 'generated_by__username']
    readonly_fields = ['generated_by', 'created_at']