from django.contrib import admin
from documents.models import Document_sto, Abstract_sto, Section, BibliographyEntry, Appendix_sto

class SectionInline(admin.TabularInline):
    model = Section
    extra = 0

class BibliographyInline(admin.TabularInline):
    model = BibliographyEntry
    extra = 0

class AppendixInline(admin.TabularInline):
    model = Appendix_sto
    extra = 0

class AbstractInline(admin.StackedInline):
    model = Abstract_sto
    extra = 0
    max_num = 1

@admin.register(Document_sto)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'work_type', 'student_name', 'year', 'city')
    search_fields = ('title', 'student_name', 'supervisor')
    list_filter = ('work_type', 'year')
    inlines = [AbstractInline, SectionInline, BibliographyInline, AppendixInline]


