from documents.models import Document_main
from django.contrib import admin
from unfold.admin import ModelAdmin


@admin.register(Document_main)
class DocumentAdmin(ModelAdmin):
    list_display = ('title', 'student_name', 'supervisor', 'created_at')
    search_fields = ('title', 'student_name', 'supervisor')
    list_filter = ('work_type', 'year')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    list_per_page = 20