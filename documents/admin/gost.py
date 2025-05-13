from django.contrib import admin
from documents.models.gost import (
    Document, TitlePage, Performer, Abstract,
    Term, Abbreviation, Reference, Appendix
)


class TitlePageInline(admin.StackedInline):
    model = TitlePage
    can_delete = False
    verbose_name_plural = 'Title Page'
    fk_name = 'document'


class AbstractInline(admin.StackedInline):
    model = Abstract
    can_delete = False
    verbose_name_plural = 'Abstract'
    fk_name = 'document'


class PerformerInline(admin.TabularInline):
    model = Performer
    extra = 1
    fk_name = 'document'


class TermInline(admin.TabularInline):
    model = Term
    extra = 1
    fk_name = 'document'


class AbbreviationInline(admin.TabularInline):
    model = Abbreviation
    extra = 1
    fk_name = 'document'


class ReferenceInline(admin.TabularInline):
    model = Reference
    extra = 1
    fk_name = 'document'
    ordering = ('order',)


class AppendixInline(admin.TabularInline):
    model = Appendix
    extra = 1
    fk_name = 'document'
    ordering = ('order',)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'template_type', 'report_type', 'year', 'created_at')
    list_filter = ('template_type', 'report_type', 'year', 'created_at')
    search_fields = ('title', 'user__username')
    inlines = [
        TitlePageInline,
        AbstractInline,
        PerformerInline,
        TermInline,
        AbbreviationInline,
        ReferenceInline,
        AppendixInline,
    ]
    ordering = ('-created_at',)


