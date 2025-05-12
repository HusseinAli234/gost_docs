from django.contrib import admin
from documents.models import Document, Abstract, Section, BibliographyEntry, Appendix

class SectionInline(admin.TabularInline):
    model = Section
    extra = 0

class BibliographyInline(admin.TabularInline):
    model = BibliographyEntry
    extra = 0

class AppendixInline(admin.TabularInline):
    model = Appendix
    extra = 0

class AbstractInline(admin.StackedInline):
    model = Abstract
    extra = 0
    max_num = 1

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'work_type', 'student_name', 'year', 'city')
    search_fields = ('title', 'student_name', 'supervisor')
    list_filter = ('work_type', 'year')
    inlines = [AbstractInline, SectionInline, BibliographyInline, AppendixInline]


